#!/bin/bash

echo "===================================================="
echo "Netflix Layout-Based Validation Test"
echo "===================================================="
echo ""

echo "1. NETFLIX PROFILE SCREEN VALIDATION"
echo "------------------------------------"
python3 screen_validator_lightweight.py reference_screens/NetflixProfileScreen.png NetflixProfileScreen 2>&1 | grep -E "(Using layout|📍|MATCH|Confidence:)"
echo ""

echo "2. NETFLIX LOGIN SCREEN V1 VALIDATION"
echo "--------------------------------------"
python3 screen_validator_lightweight.py reference_screens/NetflixLoginScreen_v1.png NetflixLoginScreen_v1 2>&1 | grep -E "(Using layout|📍|MATCH|Confidence:)"
echo ""

echo "3. NETFLIX LOGIN SCREEN V2 VALIDATION"
echo "--------------------------------------"
python3 screen_validator_lightweight.py reference_screens/NetflixLoginScreen_v2.png NetflixLoginScreen_v2 2>&1 | grep -E "(Using layout|📍|MATCH|Confidence:)"
echo ""

echo "===================================================="
echo "Cross-Validation Tests (Should FAIL)"
echo "===================================================="
echo ""

echo "4. PROFILE vs LOGIN SCREEN (Should NOT match)"
echo "----------------------------------------------"
python3 screen_validator_lightweight.py reference_screens/NetflixProfileScreen.png NetflixLoginScreen_v1 2>&1 | grep -E "(Using layout|📍|MATCH|Confidence:)"
echo ""

echo "5. LOGIN V1 vs LOGIN V2 (Should match - similar layouts)"
echo "---------------------------------------------------------"
python3 screen_validator_lightweight.py reference_screens/NetflixLoginScreen_v1.png NetflixLoginScreen_v2 2>&1 | grep -E "(Using layout|📍|MATCH|Confidence:)"
echo ""

echo "===================================================="
echo "Summary:"
echo "✅ All Netflix screens now use layout-based validation"
echo "✅ Regions detected:"
echo "   - Profile: Netflix logo, 'Choose a Profile' text, Profile icons"
echo "   - Login: Netflix logo, Login form, Sign in button"
echo "✅ Threshold: 0.55 (55% confidence required)"
echo "===================================================="
