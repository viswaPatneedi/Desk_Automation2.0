#!/bin/bash

echo "===================================================="
echo "Layout-Based HomeScreen Validation Test"
echo "===================================================="
echo ""

total=0
passed=0
failed=0

for file in screenshots/*/ITR-*/BEFORE/*.png; do
    if [ -f "$file" ]; then
        total=$((total + 1))
        device=$(basename $(dirname $(dirname $(dirname "$file"))))
        iteration=$(basename $(dirname $(dirname "$file")))
        
        echo "[$total] Testing: $device / $iteration"
        
        result=$(python3 screen_validator_lightweight.py "$file" HomeScreen 2>&1)
        
        if echo "$result" | grep -q "✓ MATCH"; then
            confidence=$(echo "$result" | grep "Layout Confidence" | sed 's/.*: //')
            echo "    ✅ PASS - Confidence: $confidence"
            echo "$result" | grep "📍"
            passed=$((passed + 1))
        else
            confidence=$(echo "$result" | grep "Confidence:" | tail -1 | awk '{print $NF}')
            echo "    ❌ FAIL - Confidence: $confidence"
            echo "$result" | grep "📍"
            failed=$((failed + 1))
        fi
        echo ""
    fi
done

echo "===================================================="
echo "Summary:"
echo "  Total: $total"
echo "  Passed: $passed ($(echo "scale=1; $passed * 100 / $total" | bc)%)"
echo "  Failed: $failed ($(echo "scale=1; $failed * 100 / $total" | bc)%)"
echo "===================================================="
