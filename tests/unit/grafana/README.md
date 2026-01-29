# Grafana Integration Unit Tests

This directory contains unit tests for Grafana dashboard and query functionality.

## Test Files

### Dashboard Tests
- **test_dashboard_queries.py** - Tests for dashboard query generation and execution
- **test_grafana_query.py** - Tests for Grafana query DSL and formatting
- **test_pie_query.py** - Tests for pie chart query generation

### Format Tests
- **test_grafana_format.py** - Tests for Grafana data formatting and transformation

## Coverage Areas

- Grafana dashboard creation and management
- Query DSL generation (InfluxDB, PostgreSQL)
- Data formatting for visualizations
- Panel configuration
- Time series transformations
- Aggregation queries

## Running Tests

```bash
# Run all Grafana tests
pytest tests/unit/grafana/ -v

# Run specific test file
pytest tests/unit/grafana/test_dashboard_queries.py -v

# Run with coverage
pytest tests/unit/grafana/ --cov=grafana --cov-report=html
```

## Related Documentation

- [Grafana Dashboard Documentation](../../docs/observability/CONTINUOUS_INTELLIGENCE_README.md)
- [Flaky Detection Dashboard](../../grafana/flaky_dashboard_fixed.json)
