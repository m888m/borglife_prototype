#!/usr/bin/env python3
"""
Analyze Current Data Structures and Dependencies for Address-Based Refactor
Maps all borg_id -> address relationships, identifies code references, documents keyring patterns,
and catalogs database queries using borg_id.
"""

import os
import re
import json
from typing import Dict, List, Set, Tuple
from datetime import datetime
import subprocess

class DataStructureAnalyzer:
    """Analyze current data structures and dependencies for the refactor."""

    def __init__(self):
        self.analysis_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'borg_id_references': {},
            'address_references': {},
            'database_queries': {},
            'keyring_patterns': {},
            'file_locations': {},
            'dependency_map': {},
            'migration_complexity': {}
        }

    def analyze_codebase(self):
        """Run comprehensive analysis of the codebase."""
        print("🔍 ANALYZING CURRENT DATA STRUCTURES AND DEPENDENCIES")
        print("=" * 70)

        self._find_borg_id_references()
        self._find_address_references()
        self._analyze_database_queries()
        self._document_keyring_patterns()
        self._map_file_dependencies()
        self._assess_migration_complexity()

        self._save_analysis_results()

    def _find_borg_id_references(self):
        """Find all references to borg_id in the codebase."""
        print("🔎 Finding borg_id references...")

        borg_id_references = {}

        # Search for borg_id patterns in Python files
        try:
            result = subprocess.run([
                'grep', '-r', '--include=*.py', 'borg_id', 'code/'
            ], capture_output=True, text=True, cwd='.')

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        # Parse file:line:content format
                        parts = line.split(':', 2)
                        if len(parts) >= 3:
                            file_path, line_num, content = parts
                            file_path = file_path.replace('./', '')

                            if file_path not in borg_id_references:
                                borg_id_references[file_path] = []

                            borg_id_references[file_path].append({
                                'line': int(line_num),
                                'content': content.strip(),
                                'context': self._classify_borg_id_usage(content)
                            })

        except Exception as e:
            print(f"⚠️  Error searching for borg_id references: {e}")

        self.analysis_results['borg_id_references'] = borg_id_references
        print(f"✅ Found borg_id references in {len(borg_id_references)} files")

    def _classify_borg_id_usage(self, content: str) -> str:
        """Classify how borg_id is being used in the code."""
        content_lower = content.lower()

        if 'def ' in content and 'borg_id' in content:
            return 'function_parameter'
        elif 'self.borg_id' in content or 'borg_id =' in content:
            return 'attribute_assignment'
        elif 'eq(' in content and 'borg_id' in content:
            return 'database_query'
        elif 'keyring' in content_lower or 'service' in content_lower:
            return 'keyring_service'
        elif 'address' in content_lower:
            return 'address_lookup'
        elif 'balance' in content_lower:
            return 'balance_operation'
        elif 'transfer' in content_lower:
            return 'transfer_operation'
        elif 'dna' in content_lower:
            return 'dna_operation'
        else:
            return 'other'

    def _find_address_references(self):
        """Find all references to blockchain addresses."""
        print("🔗 Finding address references...")

        address_references = {}

        # Search for address patterns
        address_patterns = [
            r'substrate_address',
            r'address.*=',
            r'\.address',
            r'5[0-9A-Z]{47}'  # SS58 address pattern
        ]

        for pattern in address_patterns:
            try:
                result = subprocess.run([
                    'grep', '-r', '--include=*.py', pattern, 'code/'
                ], capture_output=True, text=True, cwd='.')

                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            parts = line.split(':', 2)
                            if len(parts) >= 3:
                                file_path, line_num, content = parts
                                file_path = file_path.replace('./', '')

                                if file_path not in address_references:
                                    address_references[file_path] = []

                                address_references[file_path].append({
                                    'line': int(line_num),
                                    'content': content.strip(),
                                    'pattern': pattern
                                })

            except Exception as e:
                print(f"⚠️  Error searching for address pattern {pattern}: {e}")

        self.analysis_results['address_references'] = address_references
        print(f"✅ Found address references in {len(address_references)} files")

    def _analyze_database_queries(self):
        """Analyze database queries that use borg_id."""
        print("💾 Analyzing database queries...")

        database_queries = {
            'borg_addresses_table': [],
            'borg_balances_table': [],
            'transfer_transactions_table': [],
            'other_tables': []
        }

        # Look for database query patterns
        query_patterns = [
            (r'\.table\(.*borg_addresses.*\)', 'borg_addresses_table'),
            (r'\.table\(.*borg_balances.*\)', 'borg_balances_table'),
            (r'\.table\(.*transfer_transactions.*\)', 'transfer_transactions_table'),
            (r'\.eq\(.*borg_id.*\)', 'borg_id_queries'),
            (r'\.select\(.*borg_id.*\)', 'borg_id_selects')
        ]

        for pattern, category in query_patterns:
            try:
                result = subprocess.run([
                    'grep', '-r', '--include=*.py', pattern, 'code/'
                ], capture_output=True, text=True, cwd='.')

                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            parts = line.split(':', 2)
                            if len(parts) >= 3:
                                file_path, line_num, content = parts
                                file_path = file_path.replace('./', '')

                                query_info = {
                                    'file': file_path,
                                    'line': int(line_num),
                                    'query': content.strip(),
                                    'pattern': pattern
                                }

                                if category in database_queries:
                                    database_queries[category].append(query_info)
                                else:
                                    database_queries[category] = [query_info]

            except Exception as e:
                print(f"⚠️  Error analyzing database pattern {pattern}: {e}")

        self.analysis_results['database_queries'] = database_queries
        print(f"✅ Analyzed database queries across {len(database_queries)} categories")

    def _document_keyring_patterns(self):
        """Document current keyring service name patterns."""
        print("🔐 Documenting keyring patterns...")

        keyring_patterns = {
            'current_patterns': {
                'borg_service': 'borglife-borg-{borg_id}',
                'dispenser_service': 'borglife-dispenser',
                'address_service': 'borglife-address-{address}'  # Future pattern
            },
            'key_types': ['private_key', 'public_key', 'address'],
            'service_discovery': [],
            'migration_path': {}
        }

        # Find keyring usage patterns
        try:
            result = subprocess.run([
                'grep', '-r', '--include=*.py', 'keyring\.', 'code/'
            ], capture_output=True, text=True, cwd='.')

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                keyring_usage = []

                for line in lines:
                    if line.strip():
                        parts = line.split(':', 2)
                        if len(parts) >= 3:
                            file_path, line_num, content = parts
                            file_path = file_path.replace('./', '')

                            keyring_usage.append({
                                'file': file_path,
                                'line': int(line_num),
                                'usage': content.strip()
                            })

                keyring_patterns['service_discovery'] = keyring_usage

        except Exception as e:
            print(f"⚠️  Error documenting keyring patterns: {e}")

        # Define migration path
        keyring_patterns['migration_path'] = {
            'phase_1': 'Maintain dual keyring entries during transition',
            'phase_2': 'Migrate to address-based services',
            'phase_3': 'Remove borg_id-based services',
            'rollback': 'Restore borg_id-based services from backup'
        }

        self.analysis_results['keyring_patterns'] = keyring_patterns
        print("✅ Documented keyring service patterns and migration strategy")

    def _map_file_dependencies(self):
        """Map dependencies between files for the refactor."""
        print("🔗 Mapping file dependencies...")

        file_dependencies = {
            'core_files': [],
            'dependent_files': [],
            'test_files': [],
            'script_files': []
        }

        # Categorize files by type and importance
        important_files = [
            'code/jam_mock/borg_address_manager.py',
            'code/jam_mock/secure_borg_creation.py',
            'code/security/secure_dispenser.py',
            'code/jam_mock/inter_borg_transfer.py'
        ]

        for file_path in important_files:
            if os.path.exists(file_path):
                file_dependencies['core_files'].append({
                    'path': file_path,
                    'type': 'core',
                    'borg_id_refs': len(self.analysis_results['borg_id_references'].get(file_path, [])),
                    'address_refs': len(self.analysis_results['address_references'].get(file_path, []))
                })

        # Find script files
        script_files = []
        for root, dirs, files in os.walk('code/scripts'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    script_files.append({
                        'path': file_path,
                        'borg_id_refs': len(self.analysis_results['borg_id_references'].get(file_path, [])),
                        'address_refs': len(self.analysis_results['address_references'].get(file_path, []))
                    })

        file_dependencies['script_files'] = script_files

        # Find test files
        test_files = []
        for root, dirs, files in os.walk('code/tests'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    test_files.append({
                        'path': file_path,
                        'borg_id_refs': len(self.analysis_results['borg_id_references'].get(file_path, [])),
                        'address_refs': len(self.analysis_results['address_references'].get(file_path, []))
                    })

        file_dependencies['test_files'] = test_files

        self.analysis_results['file_locations'] = file_dependencies
        print(f"✅ Mapped dependencies across {len(script_files)} scripts and {len(test_files)} tests")

    def _assess_migration_complexity(self):
        """Assess the complexity of the migration."""
        print("📊 Assessing migration complexity...")

        # Calculate complexity metrics
        total_borg_id_refs = sum(len(refs) for refs in self.analysis_results['borg_id_references'].values())
        total_address_refs = sum(len(refs) for refs in self.analysis_results['address_references'].values())
        total_files_affected = len(self.analysis_results['borg_id_references'])

        # Database query complexity
        db_query_count = sum(len(queries) for queries in self.analysis_results['database_queries'].values())

        complexity_assessment = {
            'total_borg_id_references': total_borg_id_refs,
            'total_address_references': total_address_refs,
            'files_affected': total_files_affected,
            'database_queries_affected': db_query_count,
            'complexity_level': self._calculate_complexity_level(total_borg_id_refs, total_files_affected),
            'estimated_effort_days': self._estimate_effort(total_borg_id_refs, db_query_count),
            'risk_areas': self._identify_risk_areas()
        }

        self.analysis_results['migration_complexity'] = complexity_assessment
        print(f"✅ Migration complexity assessed: {complexity_assessment['complexity_level']} level")

    def _calculate_complexity_level(self, borg_id_refs: int, files_affected: int) -> str:
        """Calculate complexity level based on references and files."""
        if borg_id_refs > 200 or files_affected > 20:
            return 'high'
        elif borg_id_refs > 100 or files_affected > 10:
            return 'medium'
        else:
            return 'low'

    def _estimate_effort(self, borg_id_refs: int, db_queries: int) -> float:
        """Estimate effort in days for the migration."""
        # Rough estimation: 10 refs per hour, 6 hours per day
        ref_effort = (borg_id_refs / 10) / 6
        db_effort = db_queries * 0.5  # 30 minutes per DB query change
        total_effort = ref_effort + db_effort

        # Add overhead for testing and validation
        total_effort *= 1.5

        return round(total_effort, 1)

    def _identify_risk_areas(self) -> List[str]:
        """Identify high-risk areas for the migration."""
        risk_areas = []

        # Check for complex database operations
        db_queries = self.analysis_results['database_queries']
        if len(db_queries.get('borg_id_queries', [])) > 10:
            risk_areas.append('High volume of database queries using borg_id')

        # Check for core file modifications
        core_files = self.analysis_results['file_locations'].get('core_files', [])
        for file_info in core_files:
            if file_info['borg_id_refs'] > 20:
                risk_areas.append(f"Core file {file_info['path']} has many borg_id references")

        # Check for test file impact
        test_files = self.analysis_results['file_locations'].get('test_files', [])
        if len(test_files) > 5:
            risk_areas.append('Many test files need updates')

        return risk_areas

    def _save_analysis_results(self):
        """Save analysis results to JSON file."""
        output_file = f"data_structure_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)

        print(f"✅ Analysis results saved to: {output_file}")

        # Print summary
        print("\n" + "=" * 70)
        print("📊 ANALYSIS SUMMARY")
        print("=" * 70)

        complexity = self.analysis_results['migration_complexity']
        print(f"Files with borg_id references: {complexity['files_affected']}")
        print(f"Total borg_id references: {complexity['total_borg_id_references']}")
        print(f"Database queries affected: {complexity['database_queries_affected']}")
        print(f"Complexity level: {complexity['complexity_level']}")
        print(f"Estimated effort: {complexity['estimated_effort_days']} days")

        if complexity['risk_areas']:
            print("\n⚠️  RISK AREAS:")
            for risk in complexity['risk_areas']:
                print(f"  • {risk}")

        print("\n🎯 NEXT STEPS:")
        print("  1. Review core files for refactoring approach")
        print("  2. Plan database schema changes")
        print("  3. Create migration scripts")
        print("  4. Update dependent scripts systematically")


def main():
    """Run the data structure analysis."""
    analyzer = DataStructureAnalyzer()
    analyzer.analyze_codebase()


if __name__ == "__main__":
    main()