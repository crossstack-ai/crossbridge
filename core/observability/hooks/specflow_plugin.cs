/*
 * CrossBridge SpecFlow Plugin (.NET)
 * 
 * Works with Selenium .NET SpecFlow WITHOUT migration
 * 
 * Design Contract:
 * - Pure observer (sidecar)
 * - Zero changes to existing tests
 * - Tests run normally if CrossBridge unavailable
 * 
 * Installation:
 * 1. Add NuGet package: CrossBridge.SpecFlow
 * 2. Add to specflow.json:
 *    {
 *      "plugins": [
 *        {
 *          "name": "CrossBridge",
 *          "parameters": {
 *            "enabled": "true",
 *            "dbHost": "10.55.12.99",
 *            "applicationVersion": "v2.0.0"
 *          }
 *        }
 *      ]
 *    }
 */

using System;
using System.Collections.Generic;
using System.Data;
using Npgsql;
using TechTalk.SpecFlow;
using TechTalk.SpecFlow.Plugins;
using TechTalk.SpecFlow.Tracing;

[assembly: RuntimePlugin(typeof(CrossBridge.SpecFlow.CrossBridgePlugin))]

namespace CrossBridge.SpecFlow
{
    /// <summary>
    /// CrossBridge SpecFlow Plugin
    /// Pure observer - never controls test execution
    /// </summary>
    public class CrossBridgePlugin : IRuntimePlugin
    {
        public void Initialize(RuntimePluginEvents runtimePluginEvents, 
                              RuntimePluginParameters runtimePluginParameters,
                              UnitTestProviderConfiguration unitTestProviderConfiguration)
        {
            runtimePluginEvents.CustomizeTestThreadDependencies += (sender, args) =>
            {
                args.ObjectContainer.RegisterTypeAs<CrossBridgeBinding, IObserver>();
            };
        }
    }

    [Binding]
    public class CrossBridgeBinding
    {
        private readonly ScenarioContext _scenarioContext;
        private readonly FeatureContext _featureContext;
        private NpgsqlConnection _dbConnection;
        private bool _enabled;
        private DateTime _testStartTime;
        private string _applicationVersion;
        private string _productName;
        private string _environment;

        public CrossBridgeBinding(ScenarioContext scenarioContext, FeatureContext featureContext)
        {
            _scenarioContext = scenarioContext;
            _featureContext = featureContext;

            // Load configuration from environment variables or config file
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
            _productName = Environment.GetEnvironmentVariable("CROSSBRIDGE_PRODUCT_NAME") ?? "SpecFlowApp";
            _environment = Environment.GetEnvironmentVariable("CROSSBRIDGE_ENVIRONMENT") ?? "test";

            try
            {
                // Connect to PostgreSQL
                string connectionString = $"Host={dbHost};Port={dbPort};Database={dbName};Username={dbUser};Password={dbPassword}";
                _dbConnection = new NpgsqlConnection(connectionString);
                _dbConnection.Open();
                Console.WriteLine("[CrossBridge] Observer connected - monitoring test execution");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[CrossBridge] Database connection failed - tests continue normally: {ex.Message}");
                _enabled = false;
            }
        }

        [BeforeScenario]
        public void BeforeScenario()
        {
            if (!_enabled) return;

            _testStartTime = DateTime.UtcNow;

            try
            {
                string testId = GetTestId();
                string testName = _scenarioContext.ScenarioInfo.Title;
                string featureName = _featureContext.FeatureInfo.Title;
                string filePath = _featureContext.FeatureInfo.FileName;

                // Extract tags as metadata
                var metadata = new Dictionary<string, object>
                {
                    { "tags", string.Join(",", _scenarioContext.ScenarioInfo.Tags) },
                    { "feature", featureName }
                };

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
                    cmd.Parameters.AddWithValue("test_name", testName);
                    cmd.Parameters.AddWithValue("framework", "selenium-specflow-dotnet");
                    cmd.Parameters.AddWithValue("file_path", filePath);
                    cmd.Parameters.AddWithValue("status", "running");
                    cmd.Parameters.AddWithValue("application_version", _applicationVersion);
                    cmd.Parameters.AddWithValue("product_name", _productName);
                    cmd.Parameters.AddWithValue("environment", _environment);
                    cmd.Parameters.AddWithValue("event_type", "test_start");
                    cmd.Parameters.AddWithValue("event_timestamp", _testStartTime);
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

        [AfterScenario]
        public void AfterScenario()
        {
            if (!_enabled) return;

            try
            {
                string testId = GetTestId();
                string testName = _scenarioContext.ScenarioInfo.Title;
                DateTime endTime = DateTime.UtcNow;
                double durationSeconds = (endTime - _testStartTime).TotalSeconds;

                // Determine status
                string status = "passed";
                string errorMessage = null;
                string stackTrace = null;

                if (_scenarioContext.TestError != null)
                {
                    status = "failed";
                    errorMessage = _scenarioContext.TestError.Message;
                    stackTrace = _scenarioContext.TestError.StackTrace;
                }
                else if (_scenarioContext.ScenarioExecutionStatus == ScenarioExecutionStatus.TestError)
                {
                    status = "failed";
                }
                else if (_scenarioContext.ScenarioExecutionStatus == ScenarioExecutionStatus.StepDefinitionPending)
                {
                    status = "skipped";
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
                    cmd.Parameters.AddWithValue("test_name", testName);
                    cmd.Parameters.AddWithValue("framework", "selenium-specflow-dotnet");
                    cmd.Parameters.AddWithValue("file_path", _featureContext.FeatureInfo.FileName);
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
            }
            catch (Exception ex)
            {
                // Never fail the test
                Console.WriteLine($"[CrossBridge] Event emission failed (non-blocking): {ex.Message}");
            }
            finally
            {
                // Cleanup
                if (_dbConnection != null)
                {
                    _dbConnection.Close();
                    _dbConnection.Dispose();
                }
            }
        }

        private string GetTestId()
        {
            return $"{_featureContext.FeatureInfo.Title}.{_scenarioContext.ScenarioInfo.Title}";
        }
    }
}
