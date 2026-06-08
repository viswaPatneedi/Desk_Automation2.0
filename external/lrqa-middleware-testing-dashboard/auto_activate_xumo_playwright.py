#!/usr/bin/env python3
"""
Automated XUMO Device Activation Script - Playwright Version
Better cross-platform support (ARM64 + x86_64) with built-in browser management.

Follows the exact activation flow:
1. Fetch activation code from device via SSH
2. Enter activation code and check checkbox
3. Click Continue
4. Enter email/username
5. Click Continue
6. Enter password
7. Select XUMO to login
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time
import sys
import traceback

# Import activation code fetcher
try:
    from method_fetch_activation_code import fetch_xumo_activation_code
except ImportError:
    print("⚠️  Warning: method_fetch_activation_code.py not found")
    fetch_xumo_activation_code = None

# Default activation details
ACTIVATION_URL = "https://www.xumo.com/activate?execution=e1s1"
USERNAME = "vpatne290@cable.comcast.com"
PASSWORD = "Payansh!11302021"


def activate_xumo_device(device_ip=None, activation_code=None):
    """
    Automate XUMO device activation with Playwright
    
    Args:
        device_ip: IP address of XUMO device to fetch activation code from
        activation_code: Optional pre-fetched activation code
        
    Returns:
        bool: True if activation completed successfully, False otherwise
    """
    
    try:
        # Fetch activation code from device if not provided
        if not activation_code and device_ip:
            print("=" * 70)
            print("FETCHING ACTIVATION CODE FROM DEVICE")
            print("=" * 70)
            print(f"🔌 Device IP: {device_ip}")
            print("🔍 Executing: curl http://localhost:9005/as/ott")
            print("=" * 70)
            
            if fetch_xumo_activation_code:
                result = fetch_xumo_activation_code(device_ip)
                
                if result['success']:
                    activation_code = result['activation_code']
                    print(f"\n✅ Successfully fetched activation code: {activation_code}")
                    print(f"   Expiry timestamp: {result['expiry']}")
                    print(f"   Activation URI: {result['uri']}")
                else:
                    print(f"\n❌ Failed to fetch activation code: {result['message']}")
                    return False
            else:
                print("\n❌ Activation code fetcher not available")
                return False
                
        elif not activation_code:
            print("\n❌ ERROR: No activation code provided and no device IP specified")
            print("\nUsage:")
            print("  python auto_activate_xumo_playwright.py <device_ip>")
            print("  OR")
            print("  python auto_activate_xumo_playwright.py --code <activation_code>")
            return False
        
        print("\n" + "=" * 70)
        print("AUTOMATED XUMO DEVICE ACTIVATION (PLAYWRIGHT)")
        print("=" * 70)
        print(f"📱 Activation Code: {activation_code}")
        print(f"👤 Username: {USERNAME}")
        print(f"🌐 URL: {ACTIVATION_URL}")
        print("=" * 70)
        
        with sync_playwright() as p:
            # Launch browser
            print("\n🔧 Launching Chromium browser (headless mode)...")
            browser = p.chromium.launch(
                headless=True,  # Must be True for systems without X server/GUI
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            print("   ✅ Browser ready (headless)")
            
            try:
                # STEP 1: Open activation page
                print("\n[STEP 1/6] 🌐 Opening activation page...")
                print(f"   Navigating to: {ACTIVATION_URL}")
                
                # Try with longer timeout and domcontentloaded (less strict than networkidle)
                try:
                    page.goto(ACTIVATION_URL, wait_until='domcontentloaded', timeout=60000)
                    print("     ✅ Page loaded successfully (DOM ready)")
                except PlaywrightTimeout as timeout_err:
                    print(f"\n⏱️  Timeout error: {timeout_err}")
                    print("     ❌ Could not connect to XUMO activation website")
                    print("     ⚠️  This usually means:")
                    print("        1. No internet connection on Raspberry Pi")
                    print("        2. XUMO website is down or blocked")
                    print("        3. Network firewall blocking the connection")
                    print("\n     💡 Troubleshooting:")
                    print("        • Check: ping www.xumo.com")
                    print("        • Check: curl https://www.xumo.com/activate")
                    print("        • Verify Pi has working internet connection")
                    browser.close()
                    return False
                
                print(f"     Current URL: {page.url}")
                time.sleep(3)
                
                # STEP 2: Enter activation code
                print("\n[STEP 2/6] 📝 Entering activation code...")
                
                # Try multiple selectors
                code_selectors = [
                    "input[placeholder='Enter your code']",
                    "input[name='code']",
                    "input[id='activationCode']",
                    "input[type='text']"
                ]
                
                code_entered = False
                for selector in code_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        page.fill(selector, activation_code)
                        print(f"     ✅ Entered code: {activation_code}")
                        code_entered = True
                        break
                    except:
                        continue
                
                if not code_entered:
                    print("     ⚠️  Could not find code input automatically")
                    print("     Waiting 10 seconds for manual entry...")
                    time.sleep(10)
                
                time.sleep(2)
                
                # STEP 3: Check the checkbox
                print("\n[STEP 3/6] ☑️  Checking the checkbox...")
                checkbox_selectors = [
                    "input[type='checkbox']",
                    "input[role='checkbox']",
                    "[class*='checkbox']"
                ]
                
                checkbox_checked = False
                for selector in checkbox_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=3000)
                        page.check(selector)
                        print("     ✅ Checkbox checked")
                        checkbox_checked = True
                        break
                    except:
                        continue
                
                if not checkbox_checked:
                    print("     ⚠️  Checkbox not found or already checked")
                
                time.sleep(1)
                
                # STEP 4: Click Continue (after code)
                print("\n[STEP 4/6] 🔘 Clicking Continue button...")
                continue_selectors = [
                    "button:has-text('Continue')",
                    "button:has-text('CONTINUE')",
                    "button[type='submit']",
                    "input[type='submit']"
                ]
                
                continue_clicked = False
                for selector in continue_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        page.click(selector)
                        print("     ✅ Continue clicked")
                        continue_clicked = True
                        break
                    except:
                        continue
                
                if not continue_clicked:
                    print("     ⚠️  Continue button not found")
                
                time.sleep(3)
                
                # STEP 5: Enter username/email
                print("\n[STEP 5/6] 📧 Entering username/email...")
                username_selectors = [
                    "input[type='email']",
                    "input[placeholder*='email' i]",
                    "input[placeholder*='username' i]",
                    "input[name='username']",
                    "input[id='username']"
                ]
                
                username_entered = False
                for selector in username_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        page.fill(selector, USERNAME)
                        print(f"     ✅ Entered username: {USERNAME}")
                        username_entered = True
                        break
                    except:
                        continue
                
                if not username_entered:
                    print("     ⚠️  Username field not found")
                    print("     Waiting 10 seconds for manual entry...")
                    time.sleep(10)
                
                time.sleep(2)
                
                # Click "Continue with Xumo"
                print("\n[STEP 5.5/6] 🔘 Clicking 'Continue with Xumo'...")
                xumo_selectors = [
                    "button:has-text('Continue with Xumo')",
                    "button:has-text('Continue with XUMO')",
                    "button:has-text('XUMO')"
                ]
                
                xumo_clicked = False
                for selector in xumo_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        page.click(selector)
                        print("     ✅ 'Continue with Xumo' clicked")
                        xumo_clicked = True
                        break
                    except:
                        continue
                
                if not xumo_clicked:
                    print("     ⚠️  'Continue with Xumo' button not found")
                
                time.sleep(3)
                
                # STEP 6: Enter password
                print("\n[STEP 6/6] 🔑 Entering password...")
                print("   Waiting for XUMO login page...")
                time.sleep(1)
                print(f"   Current URL: {page.url}")
                print("   Looking for password input field...")
                password_selectors = [
                    "input[type='password']",
                    "input[name='password']",
                    "input[id='password']"
                ]
                
                password_entered = False
                for i, selector in enumerate(password_selectors, 1):
                    try:
                        print(f"   Attempt {i}: Trying selector '{selector}'...")
                        page.wait_for_selector(selector, timeout=5000)
                        page.fill(selector, PASSWORD)
                        print("     ✅ Password entered successfully")
                        password_entered = True
                        break
                    except Exception as e:
                        print(f"     ❌ Selector failed: {type(e).__name__}")
                        continue
                
                if not password_entered:
                    print("     ⚠️  Password field not found")
                    print("     Waiting 10 seconds for manual entry...")
                    time.sleep(10)
                
                time.sleep(2)
                
                # Click final submit/login button
                print("\n[STEP 6.5/6] 🔘 Clicking Login/Submit button...")
                print("   Looking for login/submit button...")
                submit_selectors = [
                    "button:has-text('Log in')",
                    "button:has-text('Login')",
                    "button:has-text('Sign in')",
                    "button:has-text('Submit')",
                    "button[type='submit']",
                    "input[type='submit']"
                ]
                
                submit_clicked = False
                for i, selector in enumerate(submit_selectors, 1):
                    try:
                        print(f"   Attempt {i}: Trying selector '{selector}'...")
                        page.wait_for_selector(selector, timeout=5000)
                        page.click(selector)
                        print("     ✅ Login button clicked successfully")
                        submit_clicked = True
                        break
                    except Exception as e:
                        print(f"     ❌ Selector failed: {type(e).__name__}")
                        continue
                
                if not submit_clicked:
                    print("     ⚠️  Login button not found - may have auto-submitted")
                
                print("\n   Waiting for activation to complete...")
                time.sleep(3)
                print(f"   Final URL: {page.url}")
                
                print("\n" + "=" * 70)
                print("✅ AUTOMATION COMPLETED SUCCESSFULLY")
                print("=" * 70)
                print("\n📺 Waiting 10 seconds to verify activation...")
                print("=" * 70)
                
                # Wait to see results
                time.sleep(10)
                
                return True
                
            except PlaywrightTimeout as e:
                print(f"\n⏱️  Timeout error: {e}")
                print("     Continuing despite timeout...")
                return False
                
            except Exception as e:
                print(f"\n❌ Error during automation: {e}")
                traceback.print_exc()
                return False
                
            finally:
                print("\n🔒 Closing browser...")
                browser.close()
                print("✅ Browser closed")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Activation interrupted by user (Ctrl+C)")
        return False
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Parse command line arguments
    device_ip = None
    activation_code = None
    
    if len(sys.argv) > 1:
        if "--code" in sys.argv:
            code_index = sys.argv.index("--code")
            if len(sys.argv) > code_index + 1:
                activation_code = sys.argv[code_index + 1]
                print(f"Using provided activation code: {activation_code}")
        else:
            device_ip = sys.argv[1]
            print(f"Will fetch activation code from device: {device_ip}")
    else:
        print("\n" + "=" * 70)
        print("XUMO Device Activation Script (Playwright)")
        print("=" * 70)
        print("\nUsage:")
        print("  1. Fetch code from device:")
        print("     python auto_activate_xumo_playwright.py <device_ip>")
        print("     Example: python auto_activate_xumo_playwright.py 10.0.0.126")
        print("\n  2. Use manual activation code:")
        print("     python auto_activate_xumo_playwright.py --code <code>")
        print("     Example: python auto_activate_xumo_playwright.py --code 679534")
        print("\n" + "=" * 70)
        sys.exit(1)
    
    success = activate_xumo_device(device_ip=device_ip, activation_code=activation_code)
    sys.exit(0 if success else 1)
