#!/usr/bin/env python3
"""
Sequence Data Integrity Validator
Ensures saved sequences maintain their data integrity
Prevents data loss by validating before/after operations
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from config_paths import SAVED_SEQUENCES_FILE


class SequenceIntegrityValidator:
    """Validates sequence data integrity and prevents data loss"""
    
    def __init__(self, sequences_file: str = None):
        self.sequences_file = Path(sequences_file or SAVED_SEQUENCES_FILE)
        self.critical_sequences = {
            'XUMOTV-FSR_ACTIVATION': {
                'required_min_steps': 40,
                'expected_methods': ['send_remote_keys', 'voice_command', 'screen_validation', 'wait', 'xumo_activation']
            }
        }
    
    def validate_json_structure(self, data: Dict) -> Tuple[bool, str]:
        """Validate JSON structure is correct"""
        try:
            if not isinstance(data, list):
                return False, "Root must be an array"
            
            for seq in data:
                if not isinstance(seq, dict):
                    return False, "Each sequence must be a dict"
                
                required_fields = ['sequence_id', 'name', 'queue_data']
                for field in required_fields:
                    if field not in seq:
                        return False, f"Missing required field: {field}"
                
                if not isinstance(seq['queue_data'], list):
                    return False, f"queue_data must be an array for {seq.get('name')}"
                
                # Validate each queue item
                for i, item in enumerate(seq['queue_data']):
                    if not isinstance(item, dict):
                        return False, f"{seq.get('name')} step {i+1}: must be dict"
                    if 'method' not in item:
                        return False, f"{seq.get('name')} step {i+1}: missing 'method'"
            
            return True, "JSON structure valid"
        
        except Exception as e:
            return False, f"Structure validation error: {str(e)}"
    
    def validate_critical_sequences(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate critical sequences have required data"""
        issues = []
        sequences_by_name = {seq['name']: seq for seq in data}
        
        for seq_name, requirements in self.critical_sequences.items():
            if seq_name not in sequences_by_name:
                issues.append(f"❌ {seq_name} not found in sequences")
                continue
            
            seq = sequences_by_name[seq_name]
            queue_data = seq.get('queue_data', [])
            
            # Check minimum steps
            min_steps = requirements['required_min_steps']
            if len(queue_data) < min_steps:
                issues.append(
                    f"❌ {seq_name}: Only {len(queue_data)} steps (expected ≥{min_steps})"
                )
            
            # Check all steps have required fields
            for i, item in enumerate(queue_data, 1):
                if 'method' not in item:
                    issues.append(f"❌ {seq_name} step {i}: missing 'method'")
                    continue
                
                method = item['method']
                if method not in requirements['expected_methods']:
                    issues.append(
                        f"⚠️  {seq_name} step {i}: unexpected method '{method}'"
                    )
                
                # Validate method-specific fields
                if method == 'send_remote_keys' and not item.get('remote_keys'):
                    issues.append(
                        f"⚠️  {seq_name} step {i}: send_remote_keys missing 'remote_keys'"
                    )
                elif method == 'voice_command' and not item.get('voice_text'):
                    issues.append(
                        f"⚠️  {seq_name} step {i}: voice_command missing 'voice_text'"
                    )
                elif method == 'screen_validation' and not item.get('expected_screen'):
                    issues.append(
                        f"⚠️  {seq_name} step {i}: screen_validation missing 'expected_screen'"
                    )
                elif method == 'wait' and not item.get('wait_seconds'):
                    issues.append(
                        f"⚠️  {seq_name} step {i}: wait missing 'wait_seconds'"
                    )
        
        return len(issues) == 0, issues
    
    def calculate_checksum(self, data: Dict) -> str:
        """Calculate checksum of sequence data for integrity verification"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def load_and_validate(self) -> Tuple[bool, Dict, List[str]]:
        """Load file and validate complete integrity"""
        issues = []
        data = None
        
        # Check file exists
        if not self.sequences_file.exists():
            return False, {}, [f"File not found: {self.sequences_file}"]
        
        # Load JSON
        try:
            with open(self.sequences_file) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, {}, [f"Invalid JSON: {str(e)}"]
        except Exception as e:
            return False, {}, [f"Load error: {str(e)}"]
        
        # Validate structure
        valid, msg = self.validate_json_structure(data)
        if not valid:
            issues.append(f"❌ {msg}")
            return False, data, issues
        
        # Validate critical sequences
        valid, critical_issues = self.validate_critical_sequences(data)
        if critical_issues:
            issues.extend(critical_issues)
        
        return len(issues) == 0, data, issues
    
    def create_backup_before_save(self) -> bool:
        """Create timestamped backup before modification"""
        if not self.sequences_file.exists():
            return False
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.sequences_file.parent / f"{self.sequences_file.name}.backup_{timestamp}"
            
            with open(self.sequences_file) as f:
                content = f.read()
            with open(backup_file, 'w') as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"⚠️  Backup creation failed: {e}")
            return False
    
    def validate_before_save(self, new_data: Dict) -> Tuple[bool, List[str]]:
        """Validate new data before saving"""
        issues = []
        
        # Validate structure
        valid, msg = self.validate_json_structure(new_data)
        if not valid:
            issues.append(f"❌ {msg}")
            return False, issues
        
        # Validate critical sequences preserved
        valid, critical_issues = self.validate_critical_sequences(new_data)
        if critical_issues:
            issues.extend(critical_issues)
        
        return len(issues) == 0, issues
    
    def safe_save(self, data: Dict, backup: bool = True) -> Tuple[bool, str]:
        """Safely save sequences with backup and validation"""
        # Validate before saving
        valid, issues = self.validate_before_save(data)
        if not valid:
            msg = "Save validation failed:\n" + "\n".join(issues)
            return False, msg
        
        # Create backup
        if backup and self.sequences_file.exists():
            if not self.create_backup_before_save():
                return False, "Backup creation failed"
        
        # Save to temporary file
        temp_file = self.sequences_file.parent / f"{self.sequences_file.name}.temp"
        try:
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Verify temp file is valid
            with open(temp_file) as f:
                json.load(f)
            
            # Move temp to actual file (atomic operation)
            temp_file.replace(self.sequences_file)
            return True, "Data saved successfully with all validations passed"
        
        except Exception as e:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            return False, f"Save failed: {str(e)}"
    
    def generate_report(self) -> str:
        """Generate integrity report"""
        valid, data, issues = self.load_and_validate()
        
        report = []
        report.append("=" * 70)
        report.append("SEQUENCE DATA INTEGRITY REPORT")
        report.append("=" * 70)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"File: {self.sequences_file}")
        report.append(f"Status: {'✅ VALID' if valid else '❌ INVALID'}")
        report.append("")
        
        if data:
            report.append(f"Total Sequences: {len(data)}")
            
            # Critical sequences status
            for seq_name in self.critical_sequences.keys():
                seq = next((s for s in data if s['name'] == seq_name), None)
                if seq:
                    steps = len(seq.get('queue_data', []))
                    report.append(f"  • {seq_name}: {steps} steps ✓")
                else:
                    report.append(f"  • {seq_name}: NOT FOUND ✗")
            
            # Checksum
            checksum = self.calculate_checksum(data)
            report.append(f"\nData Checksum: {checksum[:16]}...")
        
        if issues:
            report.append("\nIssues Found:")
            for issue in issues:
                report.append(f"  {issue}")
        else:
            report.append("\nNo issues found - data integrity is sound ✅")
        
        report.append("=" * 70)
        return "\n".join(report)


# Test script
if __name__ == "__main__":
    validator = SequenceIntegrityValidator()
    
    # Generate and print report
    print(validator.generate_report())
    
    # Load and validate
    valid, data, issues = validator.load_and_validate()
    
    if not valid and issues:
        print("\n⚠️  Validation issues detected:")
        for issue in issues:
            print(f"  {issue}")
        exit(1)
    else:
        print("\n✅ All integrity checks passed!")
        exit(0)
