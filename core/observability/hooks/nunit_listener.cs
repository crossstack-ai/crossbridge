/*
 * CrossBridge NUnit Listener (.NET)
 * 
 * Works with NUnit 3.x WITHOUT migration
 * 
 * Design Contract:
 * - Pure observer (sidecar)
 * - Zero changes to existing tests
 * - Tests run normally if CrossBridge unavailable
 * - Thread-safe for parallel test execution
 * 
 * Installation:
 * 1. Add NuGet packages:
 *    - Npgsql (for PostgreSQL)
 *    - NUnit 3.x
 * 
 * 2. Add to .runsettings or app.config:
 *    <NUnit>
 *      <Extensions>
 *        <add name="CrossBridge.NUnit.CrossBridgeEventListener" />
 *      </Extensions>
 *    </NUnit>
 * 
 * 3. Or use command line:
 *    dotnet test --logger:"CrossBridge"
 * 
 * 4. Set environment variables:
 *    CROSSBRIDGE_ENABLED=true
 *    CROSSBRIDGE_DB_HOST=10.55.12.99
 *    CROSSBRIDGE_APPLICATION_VERSION=v2.0.0
 */

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Data;
using Npgsql;
using NUnit.Framework;
using NUnit.Framework.Interfaces;

namespace CrossBridge.NUnit
{
    /// <summary>
    /// CrossBridge NUnit Event Listener
    /// Compatible with NUnit 3.x
    /// Pure observer - never controls test execution
    /// Thread-safe for parallel test execution
    /// </summary>
    [AttributeUsage(AttributeTargets.Assembly | AttributeTargets.Class)]
    public class CrossBridgeListenerAttribute : Attribute, ITestAction
    {
        private static readonly Lazy<CrossBridgeEventListener> _instance =
            new Lazy<CrossBridgeEventListener>(() => new CrossBridgeEventListener());

        public ActionTargets Targets => ActionTargets.Test;

        public void BeforeTest(ITest test)
        {
            _instance.Value.OnTestStarted(test);
        }

        public void AfterTest(ITest test)
        {
            _instance.Value.OnTestFinished(test);
        }
    }

    /// <summary>
    /// NUnit Event Listener - Global registration
    /// Use this for assembly-level registration
    /// </summary>
    public class CrossBridgeEventListener : ITestListener
    {
        private NpgsqlConnection _dbConnection;
        private bool _enabled;
        private string _applicationVersion;
        private string _productName;
        private string _environment;

        // Thread-safe storage for parallel test execution
        private static readonly ConcurrentDictionary<string, DateTime> _testStartTimes =
            new ConcurrentDictionary<string, DateTime>();

        public CrossBridgeEventListener()
        {
            // Load configuration from environment variables
            _enabled = Environment.GetEnvironmentVariable("CROSSBRIDGE_ENABLED") == "true";

            if (!_enabled)
            {
                Console.WriteLine("[CrossBridge] Disabled - tests run normally");
                return;
            }

            string dbHost = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_HOST") ?? "10.55.12.99";
            string dbPort = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_PORT") ?? "5432";
            string dbName = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_NAME") ?? "udp-native-webservices-automation";
            string dbUser = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_USER") ?? "postgres";
            string dbPassword = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_PASSWORD") ?? "admin";

            _applicationVersion = Environment.GetEnvironmentVariable("CROSSBRIDGE_APPLICATION_VERSION") ?? "unknown";
            _productName = Environment.GetEnvironmentVariable("CROSSBRIDGE_PRODUCT_NAME") ?? "NUnitApp";
            _environment = Environment.GetEnvironmentVariable("CROSSBRIDGE_ENVIRONMENT") ?? "test";

            try
            {
                // Connect to PostgreSQL
                string connectionString = $"Host={dbHost};Port={dbPort};Database={dbName};Username={dbUser};Password={dbPassword}";
                _dbConnection = new NpgsqlConnection(connectionString);
                _dbConnection.Open();
                Console.WriteLine("[CrossBridge] Observer connected (NUnit) - monitoring test execution");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[CrossBridge] Database connection failed - tests continue normally: {ex.Message}");
                _enabled = false;
            }
        }

        public void TestStarted(ITest test)
        {
            OnTestStarted(test);
        }

        public void TestFinished(ITestResult result)
        {
            OnTestFinished(result.Test, result);
        }

        public void TestOutput(TestOutput output)
        {
            // Optional: Capture test output
        }

        public void SendMessage(TestMessage message)
        {
            // Optional: Capture test messages
        }

        internal void OnTestStarted(ITest test)
        {
            if (!_enabled) return;

            string testId = GetTestId(test);
            DateTime startTime = DateTime.UtcNow;
            _testStartTimes.TryAdd(testId, startTime);

            try
            {
                // Extract metadata
                var metadata = new Dictionary<string, object>
                {
                    { "test_class", test.ClassName ?? "unknown" },
                    { "test_suite", test.Parent?.Name ?? "unknown" },
                    { "is_suite", test.IsSuite }
                };

                // Add properties/categories
                if (test.Properties != null && test.Properties.Keys.Count > 0)
                {
                    foreach (var key in test.Properties.Keys)
                    {
                        var values = test.Properties[key];
                        if (values != null && values.Count > 0)
                        {
                            metadata.Add($"property_{key}", string.Join(",", values));
                        }
                    }
                }

                // Emit test_start event
                using (var cmd = _dbConnection.CreateCommand())
                {
                    cmd.CommandText = @"
                        INSERT INTO test_execution_event 
                        (test_id, test_name, framework, file_path, status, 
                         application_version, product_name, environment, event_type, event_timestamp, metadata)
                        VALUES (@test_id, @test_name, @framework, @file_path, @status,
                                @application_version, @product_name, @environment, @event_type, @event_timestamp, @metadata::jsonb)";

                    cmd.Parameters.AddWithValue("test_id", testId);
                    cmd.Parameters.AddWithValue("test_name", test.Name);
                    cmd.Parameters.AddWithValue("framework", "nunit");
                    cmd.Parameters.AddWithValue("file_path", test.ClassName ?? "unknown");
                    cmd.Parameters.AddWithValue("status", "running");
                    cmd.Parameters.AddWithValue("application_version", _applicationVersion);
                    cmd.Parameters.AddWithValue("product_name", _productName);
                    cmd.Parameters.AddWithValue("environment", _environment);
                    cmd.Parameters.AddWithValue("event_type", "test_start");
                    cmd.Parameters.AddWithValue("event_timestamp", startTime);
                    cmd.Parameters.AddWithValue("metadata", System.Text.Json.JsonSerializer.Serialize(metadata));

                    cmd.ExecuteNonQuery();
                }
            }
            catch (Exception ex)
            {
                // Never fail the test
                Console.WriteLine($"[CrossBridge] Event emission failed (non-blocking): {ex.Message}");
            }
        }

        internal void OnTestFinished(ITest test, ITestResult result = null)
        {
            if (!_enabled) return;

            string testId = GetTestId(test);
            DateTime endTime = DateTime.UtcNow;

            _testStartTimes.TryGetValue(testId, out DateTime startTime);
            double durationSeconds = (endTime - startTime).TotalSeconds;

            try
            {
                // Determine status
                string status = "passed";
                string errorMessage = null;
                string stackTrace = null;

                if (result != null)
                {
                    switch (result.ResultState.Status)
                    {
                        case TestStatus.Passed:
                            status = "passed";
                            break;
                        case TestStatus.Failed:
                            status = "failed";
                            errorMessage = result.Message;
                            stackTrace = result.StackTrace;
                            break;
                        case TestStatus.Skipped:
                        case TestStatus.Inconclusive:
                            status = "skipped";
                            errorMessage = result.Message;
                            break;
                    }
                }

                // Emit test_end event
                using (var cmd = _dbConnection.CreateCommand())
                {
                    cmd.CommandText = @"
                        INSERT INTO test_execution_event 
                        (test_id, test_name, framework, file_path, status, duration_seconds,
                         error_message, stack_trace,
                         application_version, product_name, environment, event_type, event_timestamp)
                        VALUES (@test_id, @test_name, @framework, @file_path, @status, @duration_seconds,
                                @error_message, @stack_trace,
                                @application_version, @product_name, @environment, @event_type, @event_timestamp)";

                    cmd.Parameters.AddWithValue("test_id", testId);
                    cmd.Parameters.AddWithValue("test_name", test.Name);
                    cmd.Parameters.AddWithValue("framework", "nunit");
                    cmd.Parameters.AddWithValue("file_path", test.ClassName ?? "unknown");
                    cmd.Parameters.AddWithValue("status", status);
                    cmd.Parameters.AddWithValue("duration_seconds", durationSeconds);
                    cmd.Parameters.AddWithValue("error_message", (object)errorMessage ?? DBNull.Value);
                    cmd.Parameters.AddWithValue("stack_trace", (object)stackTrace ?? DBNull.Value);
                    cmd.Parameters.AddWithValue("application_version", _applicationVersion);
                    cmd.Parameters.AddWithValue("product_name", _productName);
                    cmd.Parameters.AddWithValue("environment", _environment);
                    cmd.Parameters.AddWithValue("event_type", "test_end");
                    cmd.Parameters.AddWithValue("event_timestamp", endTime);

                    cmd.ExecuteNonQuery();
                }

                // Cleanup
                _testStartTimes.TryRemove(testId, out _);
            }
            catch (Exception ex)
            {
                // Never fail the test
                Console.WriteLine($"[CrossBridge] Event emission failed (non-blocking): {ex.Message}");
            }
        }

        private string GetTestId(ITest test)
        {
            if (!string.IsNullOrEmpty(test.FullName))
            {
                return test.FullName;
            }
            return $"{test.ClassName}.{test.MethodName ?? test.Name}";
        }

        ~CrossBridgeEventListener()
        {
            if (_dbConnection != null)
            {
                try
                {
                    _dbConnection.Close();
                    _dbConnection.Dispose();
                    Console.WriteLine("[CrossBridge] Observer disconnected");
                }
                catch
                {
                    // Ignore cleanup errors
                }
            }
        }
    }

    /// <summary>
    /// Extension for NUnit Engine
    /// Allows registration at engine level
    /// </summary>
    public class CrossBridgeExtension : NUnit.Engine.Extensibility.ITestEventListener
    {
        private readonly CrossBridgeEventListener _listener;

        public CrossBridgeExtension()
        {
            _listener = new CrossBridgeEventListener();
        }

        public void OnTestEvent(string report)
        {
            // Parse NUnit XML report and forward to listener
            // This is for engine-level integration
        }
    }
}
