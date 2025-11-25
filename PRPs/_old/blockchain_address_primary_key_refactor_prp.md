# Blockchain Address Primary Key Refactor PRP

## Feature: Address-Based Primary Key System

## Goal

Refactor the BorgLife system to use blockchain addresses (e.g., Westend SS58 addresses) as the primary unique identifier for all participants, replacing name-based or ID-based identifiers. This ensures consistency with blockchain-native addressing and eliminates lookup mismatches.

## Deliverable

A fully refactored system where:
- All database entries use blockchain addresses as primary keys
- Keyring services are address-based
- All lookups and references use addresses exclusively
- Backward compatibility maintained through migration
- Comprehensive error handling prevents reconstruction failures

## Context

### Current State
- Borgs identified by `borg_id` (e.g., "borgTest1_1762870300")
- Keyring services use pattern: `borglife-borg-{borg_id}`
- Database uses `borg_id` as primary key
- Address stored as separate field
- Keypair reconstruction errors occur due to None comparisons

### Target State
- Borgs identified by blockchain address (e.g., "5EeeSsZAzVzZjTnLA9yCV8pwsuQvbHDfYPZX5YcmitVFFA2c")
- Keyring services use pattern: `borglife-address-{address}`
- Database uses `address` as primary key
- ID becomes secondary identifier
- Robust error handling prevents all reconstruction failures

### Related Files
- `code/jam_mock/borg_address_manager.py`
- `code/jam_mock/secure_borg_creation.py`
- `code/security/secure_dispenser.py`
- `code/scripts/borg_to_dispenser_transfer.py`
- `code/scripts/check_keyring.py`

### Directory Structure Changes
- **Logs**: All `.json` result files moved to dedicated `logs/` directory
- **Encrypted Assets**: All `.enc` keystore files moved to dedicated `encrypted/` directory
- **Scripts**: `code/scripts/` now contains only executable scripts and documentation
- **Future Logging**: All new log files must be written to `logs/` directory
- **Security**: Encrypted assets isolated in `encrypted/` for better access control

## Implementation Tasks

### Phase 1: Backup & Analysis
1. **Create comprehensive backup**
   - Backup all keyring entries
   - Export database to JSON/CSV
   - Document current keyring service mappings
   - Create rollback script

2. **Analyze current data**
   - Map all borg_id -> address relationships
   - Identify all code references to borg_id vs address
   - Document keyring service name patterns
   - Catalog all database queries using borg_id

### Phase 2: Core Refactoring

3. **Update BorgAddressManager**
   - Change primary key from `borg_id` to `address`
   - Update all database queries
   - Modify `get_borg_address()` to use address directly
   - Update `register_borg_address()` to use address as key

4. **Refactor Keyring Services**
   - Change service name pattern to `borglife-address-{address}`
   - Update `_store_keypair_in_keychain()` method
   - Modify all keyring access methods
   - Ensure backward compatibility during transition

5. **Enhance Keypair Reconstruction**
   - Add robust None checking before all operations
   - Implement proper error handling for hex decoding
   - Add validation for key component lengths
   - Ensure SS58 format consistency (ss58_format=42)
   - Add detailed error messages for debugging

6. **Update Secure Dispenser**
   - Modify dispenser keyring service to use address
   - Update keystore metadata structure
   - Ensure dispenser address-based identification

### Phase 3: Migration & Testing

7. **Create Migration Script**
   - Migrate existing database entries
   - Update keyring service names
   - Preserve all existing keypairs
   - Validate data integrity post-migration

8. **Update Dependent Scripts**
   - Modify `borg_to_dispenser_transfer.py`
   - Update `check_keyring.py`
   - Refactor creation scripts
   - Update all test scripts

9. **Comprehensive Testing**
   - Test keypair reconstruction with all edge cases
   - Verify address-based lookups
   - Test migration with real data
   - Validate error handling

### Phase 4: Validation & Rollback

10. **Validation Gates**
    - All keypairs reconstructable without errors
    - All database queries work with address primary key
    - Keyring access reliable for all addresses
    - No data loss during migration

11. **Rollback Procedures**
    - Restore keyring from backup
    - Revert database schema
    - Restore original service names
    - Validate system returns to pre-refactor state

## Validation Gates

### Pre-Implementation
- [ ] Backup completed and verified
- [ ] All current borg_id -> address mappings documented
- [ ] Test environment set up with copy of production data

### Post-Implementation
- [ ] All keypair reconstructions succeed without errors
- [ ] Address-based lookups work for all existing borgs
- [ ] Database queries perform correctly with address primary key
- [ ] Keyring services accessible using new naming pattern
- [ ] Migration script preserves all data integrity

### Production Readiness
- [ ] Full test suite passes with refactored code
- [ ] Performance benchmarks meet requirements
- [ ] Rollback procedures tested and documented
- [ ] Monitoring alerts configured for new error patterns

## Risks & Mitigations

### High Risk: Data Loss
- **Risk**: Migration corrupts keyring or database
- **Mitigation**: Comprehensive backups, staged migration, rollback procedures

### High Risk: Keypair Inaccessibility
- **Risk**: Refactored keyring services make keys unreachable
- **Mitigation**: Maintain backward compatibility, test all access patterns

### Medium Risk: Address Conflicts
- **Risk**: Multiple borgs with same address (shouldn't happen)
- **Mitigation**: Add unique constraints, validate during migration

### Medium Risk: Performance Impact
- **Risk**: Address-based lookups slower than ID-based
- **Mitigation**: Add proper indexing, benchmark performance

## Testing Strategy

### Unit Tests
- Keypair reconstruction with various inputs
- Address validation and formatting
- Database query modifications
- Keyring service name generation

### Integration Tests
- Full borg creation workflow
- Transfer operations with address-based keys
- Migration script execution
- Rollback procedure validation

### End-to-End Tests
- Complete user workflows
- Error scenario handling
- Performance under load
- Data integrity validation

## Success Criteria

1. **Zero Keypair Reconstruction Errors**: All keypairs reconstruct successfully without "'<' not supported between instances of 'NoneType' and 'int'" or similar errors

2. **Address-Based Consistency**: All system components use blockchain addresses as primary identifiers

3. **Backward Compatibility**: Existing data migrates cleanly with no loss

4. **Error Handling Robustness**: Comprehensive error handling prevents all None-related comparison errors

5. **Performance Maintenance**: No significant performance degradation from ID to address-based lookups

## Rollback Procedures

### Immediate Rollback (< 1 hour)
1. Stop all services
2. Restore keyring from backup
3. Run database schema rollback script
4. Restart services
5. Verify system returns to pre-refactor state

### Data Recovery Rollback (< 4 hours)
1. Restore from database backup
2. Recreate keyring services with original names
3. Rebuild keystore files
4. Validate all keypairs accessible
5. Full system testing

### Emergency Rollback (< 15 minutes)
1. Switch to backup environment
2. Redirect traffic to backup
3. Investigate primary environment offline
4. Plan recovery or permanent rollback

## Dependencies

- Substrate interface library for address validation
- Keyring library for secure storage access
- Database access for schema modifications
- Testing framework for validation
- Backup systems for data preservation

## Timeline

- **Phase 1**: 2-3 days (backup, analysis, planning)
- **Phase 2**: 5-7 days (core refactoring)
- **Phase 3**: 3-4 days (migration, testing)
- **Phase 4**: 1-2 days (validation, documentation)

Total: 11-16 days for complete refactor with full testing and rollback capabilities.