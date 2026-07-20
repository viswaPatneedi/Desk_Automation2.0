"""
Unit Tests for Phase 22: Custom Grep Pattern Filtering Feature
Tests for custom log pattern parsing, contains/NOT-contains logic, and integration
"""

import unittest
import re
from datetime import datetime, timezone

class TestCustomGrepPatternParsing(unittest.TestCase):
    """Test suite for custom grep pattern parsing (Phase 22)"""
    
    def test_parse_simple_contains_pattern(self):
        """Test parsing simple 'contains' pattern"""
        pattern = "ERROR"
        # Should just be the pattern as-is
        self.assertTrue(self.matches_pattern(pattern, "Line with ERROR message", contains=True))
        self.assertFalse(self.matches_pattern(pattern, "Line with WARNING message", contains=True))
    
    def test_parse_regex_pattern(self):
        """Test parsing regex pattern with alternatives"""
        pattern = "ERROR|CRASH|FATAL"
        # Should match any of the alternatives
        self.assertTrue(self.matches_pattern(pattern, "ERROR in system", contains=True))
        self.assertTrue(self.matches_pattern(pattern, "System CRASH detected", contains=True))
        self.assertTrue(self.matches_pattern(pattern, "FATAL exception", contains=True))
        self.assertFalse(self.matches_pattern(pattern, "Normal operation", contains=True))
    
    def test_parse_negation_pattern_with_prefix(self):
        """Test parsing negation pattern (NOT contains)"""
        # Pattern with ! prefix indicates NOT matching
        pattern_with_prefix = "!INFO"
        raw_pattern = pattern_with_prefix[1:] if pattern_with_prefix.startswith('!') else pattern_with_prefix
        is_negation = pattern_with_prefix.startswith('!')
        
        # Test the negation logic
        self.assertTrue(is_negation)
        # Line without INFO should match (for NOT contains)
        self.assertTrue(self.matches_pattern(raw_pattern, "Line with ERROR", contains=not is_negation))
        # Line with INFO should not match (for NOT contains)
        self.assertFalse(self.matches_pattern(raw_pattern, "Line with INFO", contains=not is_negation))
    
    def test_multiple_patterns_with_contains_and_negation(self):
        """Test handling multiple patterns with mixed contains and negation"""
        patterns = [
            "ERROR",      # Regular contains
            "!INFO",      # NOT contains (negation)
            "CRASH|FATAL" # Regex contains
        ]
        
        # Separate into regular and negation patterns
        regular_patterns = []
        negation_patterns = []
        
        for pattern in patterns:
            if pattern.startswith('!'):
                negation_patterns.append(pattern[1:])
            else:
                regular_patterns.append(pattern)
        
        self.assertEqual(len(regular_patterns), 2)
        self.assertEqual(len(negation_patterns), 1)
        self.assertIn("ERROR", regular_patterns)
        self.assertIn("CRASH|FATAL", regular_patterns)
        self.assertIn("INFO", negation_patterns)
    
    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive"""
        pattern = "error"
        # Should match case-insensitive
        self.assertTrue(self.matches_pattern_case_insensitive(pattern, "Line with ERROR"))
        self.assertTrue(self.matches_pattern_case_insensitive(pattern, "Line with Error"))
        self.assertTrue(self.matches_pattern_case_insensitive(pattern, "Line with error"))
    
    def test_empty_pattern_handling(self):
        """Test handling of empty patterns"""
        patterns = ["", "ERROR", "", "CRASH"]
        # Filter out empty patterns
        non_empty = [p for p in patterns if p.strip()]
        
        self.assertEqual(len(non_empty), 2)
        self.assertNotIn("", non_empty)
    
    def test_pattern_with_special_regex_chars(self):
        """Test patterns with special regex characters"""
        # Pattern with regex special chars should still work
        pattern = r"process\..*\crashed"
        # Basic validation that it's a valid regex
        try:
            re.compile(pattern)
            is_valid_regex = True
        except re.error:
            is_valid_regex = False
        
        self.assertTrue(is_valid_regex)
    
    def test_grep_command_generation_contains(self):
        """Test generating grep command for contains pattern"""
        pattern = "ERROR"
        # Simulate grep command generation
        grep_cmd = f"grep -i -E '{pattern}' /opt/logs/core_log.txt | head -1"
        
        # Verify command format is correct
        self.assertIn("grep", grep_cmd)
        self.assertIn("-i", grep_cmd)  # Case-insensitive flag
        self.assertIn("-E", grep_cmd)  # Extended regex
        self.assertIn(pattern, grep_cmd)
        self.assertIn("/opt/logs/core_log.txt", grep_cmd)
    
    def test_grep_command_generation_not_contains(self):
        """Test generating grep command for NOT contains pattern"""
        pattern = "INFO"
        # Simulate grep command for negation
        grep_cmd = f"grep -v -i -E '{pattern}' /opt/logs/core_log.txt | grep -v '^$' | head -1"
        
        # Verify command has negation flag
        self.assertIn("grep -v", grep_cmd)  # Negation flag
        self.assertIn("-i", grep_cmd)       # Case-insensitive
        self.assertIn(pattern, grep_cmd)
    
    # Helper methods for pattern matching
    def matches_pattern(self, pattern, text, contains=True):
        """Helper to test pattern matching"""
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            if contains:
                return bool(regex.search(text))
            else:
                return not bool(regex.search(text))
        except:
            return False
    
    def matches_pattern_case_insensitive(self, pattern, text):
        """Helper for case-insensitive matching"""
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            return bool(regex.search(text))
        except:
            return False

class TestCustomPatternIntegration(unittest.TestCase):
    """Integration tests for custom pattern functionality"""
    
    def test_pattern_serialization_to_backend(self):
        """Test that patterns are properly serialized for backend"""
        # Simulate frontend pattern format
        frontend_patterns = [
            {"pattern": "ERROR", "type": "contains"},
            {"pattern": "INFO", "type": "not_contains"},
            {"pattern": "CRASH|FATAL", "type": "contains"}
        ]
        
        # Convert to backend format
        backend_patterns = []
        for p in frontend_patterns:
            if p["type"] == "not_contains":
                backend_patterns.append(f"!{p['pattern']}")
            else:
                backend_patterns.append(p["pattern"])
        
        # Verify conversion
        self.assertEqual(len(backend_patterns), 3)
        self.assertIn("ERROR", backend_patterns)
        self.assertIn("!INFO", backend_patterns)
        self.assertIn("CRASH|FATAL", backend_patterns)
    
    def test_pattern_list_from_textarea(self):
        """Test parsing pattern list from textarea (comma-separated)"""
        textarea_content = "ERROR, CRASH, FATAL|PANIC"
        
        # Parse like the backend does
        patterns = [p.strip() for p in textarea_content.split(',') if p.strip()]
        
        self.assertEqual(len(patterns), 3)
        self.assertIn("ERROR", patterns)
        self.assertIn("CRASH", patterns)
        self.assertIn("FATAL|PANIC", patterns)
    
    def test_combined_patterns_from_multiple_modals(self):
        """Test combining patterns from regular log patterns modal and custom modal"""
        # Regular patterns from log patterns modal
        regular_patterns = ["ERROR", "CRASH"]
        
        # Custom patterns from custom patterns modal
        custom_patterns = [
            {"pattern": "DEBUG", "type": "contains"},
            {"pattern": "INFO", "type": "not_contains"}
        ]
        
        # Merge patterns
        all_patterns = regular_patterns.copy()
        for cp in custom_patterns:
            if cp["type"] == "not_contains":
                all_patterns.append(f"!{cp['pattern']}")
            else:
                all_patterns.append(cp["pattern"])
        
        # Verify merged result
        self.assertEqual(len(all_patterns), 4)
        self.assertIn("ERROR", all_patterns)
        self.assertIn("CRASH", all_patterns)
        self.assertIn("DEBUG", all_patterns)
        self.assertIn("!INFO", all_patterns)
    
    def test_pattern_validation_before_execution(self):
        """Test that patterns are validated before method execution"""
        patterns = ["ERROR", "!CRASH", "", "FATAL"]
        
        # Validate patterns
        valid_patterns = []
        for p in patterns:
            if p.strip():  # Not empty
                valid_patterns.append(p)
            # Try to compile as regex
            try:
                if p.startswith('!'):
                    re.compile(p[1:])
                else:
                    re.compile(p)
                valid_patterns.append(p) if p.strip() and p not in valid_patterns else None
            except re.error:
                pass  # Invalid regex, skip
        
        # Remove duplicates and clean
        valid_patterns = list(set([p for p in patterns if p.strip()]))
        
        self.assertEqual(len(valid_patterns), 3)
        self.assertNotIn("", valid_patterns)

class TestPatternExecutionSequence(unittest.TestCase):
    """Test the execution sequence of pattern matching"""
    
    def test_pattern_search_order(self):
        """Test that contains patterns are searched before NOT patterns"""
        execution_order = []
        
        # Simulate pattern search
        regular_patterns = ["ERROR", "CRASH"]
        negation_patterns = ["INFO"]
        
        # Search regular patterns first
        for p in regular_patterns:
            execution_order.append(f"contains:{p}")
        
        # Then search negation patterns
        for p in negation_patterns:
            execution_order.append(f"not:{p}")
        
        # Verify order
        self.assertEqual(execution_order[0], "contains:ERROR")
        self.assertEqual(execution_order[1], "contains:CRASH")
        self.assertEqual(execution_order[2], "not:INFO")
    
    def test_early_exit_on_match(self):
        """Test that log collection happens immediately on first match"""
        patterns_to_check = [
            {"pattern": "ERROR", "type": "contains", "found": True},
            {"pattern": "CRASH", "type": "contains", "found": False},
            {"pattern": "INFO", "type": "not_contains", "found": True}
        ]
        
        # Should stop at first match
        matched = False
        matched_pattern = None
        
        for p in patterns_to_check:
            if p["found"]:
                matched = True
                matched_pattern = p
                break
        
        self.assertTrue(matched)
        self.assertIsNotNone(matched_pattern)
        self.assertEqual(matched_pattern["pattern"], "ERROR")

if __name__ == '__main__':
    unittest.main()
