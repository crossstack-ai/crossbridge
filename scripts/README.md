# Scripts Directory

**Last Updated**: January 29, 2026

## Overview

Utility scripts for CrossBridge development, testing, and maintenance organized by purpose.

## Directory Structure

```
scripts/
‚îú‚îÄ‚îÄ demos/              # Demo scripts showcasing features
‚îú‚îÄ‚îÄ utilities/          # Development and setup utilities
‚îú‚îÄ‚îÄ maintenance/        # Database and system maintenance
‚îú‚îÄ‚îÄ validation/         # System validation and verification
‚îî‚îÄ‚îÄ [legacy scripts]    # Database and migration scripts
```

## Categories

### Ì≥∫ Demos (`demos/`)
Example scripts demonstrating CrossBridge features:
- AI transformation demos
- Flaky detection demos
- Memory/embedding demos
- Continuous intelligence demos

**Usage**: Run to see features in action, ideal for learning and presentations.

### Ì¥ß Utilities (`utilities/`)
Development and setup utilities:
- Dashboard creation and updates
- Data generation
- Database population
- Quick test runners

**Usage**: Development tools for setting up and testing the system.

### Ìª†Ô∏è Maintenance (`maintenance/`)
System maintenance scripts:
- Bug fixes and patches
- Database schema fixes
- Mock data cleanup
- Test fixture maintenance

**Usage**: One-time or periodic maintenance tasks.

### ‚úÖ Validation (`validation/`)
System verification and checking:
- Data source verification
- Schema validation
- Integration checks
- Production readiness verification

**Usage**: Verify system state and validate configurations.

## Quick Reference

| Prefix | Category | Location | Purpose |
|--------|----------|----------|---------|
| `demo_*` | Demos | `demos/` | Feature demonstrations |
| `create_*` | Utilities | `utilities/` | Creation/generation tools |
| `generate_*` | Utilities | `utilities/` | Data generation |
| `populate_*` | Utilities | `utilities/` | Database population |
| `setup_*` | Utilities | `utilities/` | System setup |
| `quick_*` | Utilities | `utilities/` | Quick test/run scripts |
| `fix_*` | Maintenance | `maintenance/` | Bug fixes |
| `update_*` | Maintenance | `maintenance/` | Update scripts |
| `check_*` | Validation | `validation/` | Verification checks |
| `verify_*` | Validation | `validation/` | Validation scripts |
| `debug_*` | Validation | `validation/` | Debug utilities |
| `diagnose_*` | Validation | `validation/` | Diagnostic tools |

## Running Scripts

### From Root Directory
```bash
# Run a demo
python scripts/demos/demo_ai_summary.py

# Run a utility
python scripts/utilities/generate_recent_data.py

# Run validation
python scripts/validation/check_datasource.py
```

### From Scripts Directory
```bash
cd scripts
python demos/demo_flaky_detection.py
python utilities/populate_profiling_sample_data.py
python validation/verify_grafana_queries.py
```

## Legacy Scripts

Scripts in the root `scripts/` directory (not in subdirectories) are legacy database/migration scripts that are still actively used:
- `setup_comprehensive_schema.py`
- `migrate_*.py`
- `generate_embeddings.py`
- etc.

These should remain in the scripts root for backward compatibility.

## Contributing

When adding new scripts:
1. Choose the appropriate category
2. Use consistent naming (prefix_descriptive_name.py)
3. Add docstring explaining purpose
4. Update this README if adding new categories
5. Include usage examples in docstring

---

**Maintained by**: CrossStack AI  
**License**: Apache 2.0
