"""
.NET NUnit Hook for Performance Profiling

Generates C# code for NUnit integration.
"""

NUNIT_HOOK_CSHARP = """
using NUnit.Framework;
using NUnit.Framework.Interfaces;
using System;
using System.Data;
using Npgsql;
using System.Collections.Generic;

namespace CrossBridge.Profiling
{
    /// <summary>
    /// CrossBridge Performance Profiling Hook for NUnit
    /// 
    /// Usage:
    /// [assembly: CrossBridge.Profiling.CrossBridgeProfilingHook]
    /// </summary>
    [AttributeUsage(AttributeTargets.Assembly)]
    public class CrossBridgeProfilingHookAttribute : Attribute, ITestAction
    {
        private static readonly string RunId = Guid.NewGuid().ToString();
        private static readonly bool Enabled = 
            Environment.GetEnvironmentVariable("CROSSBRIDGE_PROFILING_ENABLED") == "true";
        
        private static NpgsqlConnection connection;
        private static Dictionary<string, DateTime> testStartTimes = new Dictionary<string, DateTime>();
        
        public ActionTargets Targets => ActionTargets.Test;
        
        public void BeforeTest(ITest test)
        {
            if (!Enabled) return;
            
            var testId = GetTestId(test);
            testStartTimes[testId] = DateTime.UtcNow;
            
            try
            {
                EnsureConnection();
                InsertEvent(testId, "test_start", 0, "unknown");
            }
            catch (Exception ex)
            {
                // Silent failure
                Console.WriteLine($"[CrossBridge Profiling] Error: {ex.Message}");
            }
        }
        
        public void AfterTest(ITest test)
        {
            if (!Enabled) return;
            
            var testId = GetTestId(test);
            
            if (testStartTimes.TryGetValue(testId, out DateTime startTime))
            {
                try
                {
                    var duration = (DateTime.UtcNow - startTime).TotalMilliseconds;
                    var status = TestContext.CurrentContext.Result.Outcome.Status.ToString().ToLower();
                    
                    InsertEvent(testId, "test_end", (int)duration, status);
                }
                catch (Exception ex)
                {
                    // Silent failure
                    Console.WriteLine($"[CrossBridge Profiling] Error: {ex.Message}");
                }
                finally
                {
                    testStartTimes.Remove(testId);
                }
            }
        }
        
        private static string GetTestId(ITest test)
        {
            return $"{test.ClassName}.{test.MethodName}";
        }
        
        private static void EnsureConnection()
        {
            if (connection != null && connection.State == ConnectionState.Open)
                return;
            
            var host = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_HOST") ?? "localhost";
            var port = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_PORT") ?? "5432";
            var database = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_NAME") ?? "crossbridge";
            var user = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_USER") ?? "postgres";
            var password = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_PASSWORD") ?? "";
            
            var connectionString = $"Host={host};Port={port};Database={database};Username={user};Password={password}";
            connection = new NpgsqlConnection(connectionString);
            connection.Open();
            
            Console.WriteLine($"[CrossBridge Profiling] Enabled for run: {RunId}");
        }
        
        private static void InsertEvent(string testId, string eventType, int duration, string status)
        {
            if (connection == null) return;
            
            try
            {
                var sql = @"
                    INSERT INTO profiling.tests 
                    (run_id, test_id, duration_ms, status, framework, created_at)
                    VALUES (@run_id, @test_id, @duration, @status, @framework, @created_at)";
                
                using (var cmd = new NpgsqlCommand(sql, connection))
                {
                    cmd.Parameters.AddWithValue("run_id", Guid.Parse(RunId));
                    cmd.Parameters.AddWithValue("test_id", testId);
                    cmd.Parameters.AddWithValue("duration", duration);
                    cmd.Parameters.AddWithValue("status", status);
                    cmd.Parameters.AddWithValue("framework", "nunit");
                    cmd.Parameters.AddWithValue("created_at", DateTime.UtcNow);
                    
                    cmd.ExecuteNonQuery();
                }
            }
            catch (Exception ex)
            {
                // Silent failure
                Console.WriteLine($"[CrossBridge Profiling] Failed to insert event: {ex.Message}");
            }
        }
        
        [OneTimeTearDown]
        public static void Cleanup()
        {
            if (connection != null)
            {
                try
                {
                    connection.Close();
                    connection.Dispose();
                    Console.WriteLine("[CrossBridge Profiling] Session complete");
                }
                catch
                {
                    // Silent failure
                }
            }
        }
    }
}
"""

SPECFLOW_HOOK_CSHARP = """
using TechTalk.SpecFlow;
using System;
using System.Data;
using Npgsql;

namespace CrossBridge.Profiling
{
    /// <summary>
    /// CrossBridge Performance Profiling Hook for SpecFlow
    /// 
    /// Add this class to your SpecFlow project.
    /// </summary>
    [Binding]
    public class CrossBridgeSpecFlowHook
    {
        private static readonly string RunId = Guid.NewGuid().ToString();
        private static readonly bool Enabled = 
            Environment.GetEnvironmentVariable("CROSSBRIDGE_PROFILING_ENABLED") == "true";
        
        private static NpgsqlConnection connection;
        private DateTime scenarioStartTime;
        
        [BeforeTestRun]
        public static void BeforeTestRun()
        {
            if (!Enabled) return;
            
            try
            {
                var host = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_HOST") ?? "localhost";
                var port = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_PORT") ?? "5432";
                var database = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_NAME") ?? "crossbridge";
                var user = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_USER") ?? "postgres";
                var password = Environment.GetEnvironmentVariable("CROSSBRIDGE_DB_PASSWORD") ?? "";
                
                var connectionString = $"Host={host};Port={port};Database={database};Username={user};Password={password}";
                connection = new NpgsqlConnection(connectionString);
                connection.Open();
                
                Console.WriteLine($"[CrossBridge Profiling] Enabled for run: {RunId}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[CrossBridge Profiling] Failed to initialize: {ex.Message}");
            }
        }
        
        [BeforeScenario]
        public void BeforeScenario(ScenarioContext scenarioContext)
        {
            if (!Enabled) return;
            
            scenarioStartTime = DateTime.UtcNow;
            
            try
            {
                var testId = GetScenarioId(scenarioContext);
                InsertEvent(testId, "test_start", 0, "unknown");
            }
            catch
            {
                // Silent failure
            }
        }
        
        [AfterScenario]
        public void AfterScenario(ScenarioContext scenarioContext)
        {
            if (!Enabled) return;
            
            try
            {
                var duration = (DateTime.UtcNow - scenarioStartTime).TotalMilliseconds;
                var testId = GetScenarioId(scenarioContext);
                var status = scenarioContext.TestError == null ? "passed" : "failed";
                
                InsertEvent(testId, "test_end", (int)duration, status);
            }
            catch
            {
                // Silent failure
            }
        }
        
        [AfterTestRun]
        public static void AfterTestRun()
        {
            if (!Enabled) return;
            
            try
            {
                if (connection != null)
                {
                    connection.Close();
                    connection.Dispose();
                    Console.WriteLine("[CrossBridge Profiling] Session complete");
                }
            }
            catch
            {
                // Silent failure
            }
        }
        
        private string GetScenarioId(ScenarioContext scenarioContext)
        {
            return $"{scenarioContext.ScenarioInfo.Title}";
        }
        
        private void InsertEvent(string testId, string eventType, int duration, string status)
        {
            if (connection == null) return;
            
            try
            {
                var sql = @"
                    INSERT INTO profiling.tests 
                    (run_id, test_id, duration_ms, status, framework, created_at)
                    VALUES (@run_id, @test_id, @duration, @status, @framework, @created_at)";
                
                using (var cmd = new NpgsqlCommand(sql, connection))
                {
                    cmd.Parameters.AddWithValue("run_id", Guid.Parse(RunId));
                    cmd.Parameters.AddWithValue("test_id", testId);
                    cmd.Parameters.AddWithValue("duration", duration);
                    cmd.Parameters.AddWithValue("status", status);
                    cmd.Parameters.AddWithValue("framework", "specflow");
                    cmd.Parameters.AddWithValue("created_at", DateTime.UtcNow);
                    
                    cmd.ExecuteNonQuery();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[CrossBridge Profiling] Failed to insert event: {ex.Message}");
            }
        }
    }
}
"""

def create_dotnet_profiling_hooks(output_dir: str = "CrossBridge.Profiling"):
    """
    Create .NET profiling hook files.
    
    Returns:
        Dictionary mapping filenames to their content
    """
    return {
        "CrossBridgeProfilingHook.cs": NUNIT_HOOK_CSHARP,
        "CrossBridgeSpecFlowHook.cs": SPECFLOW_HOOK_CSHARP,
    }
