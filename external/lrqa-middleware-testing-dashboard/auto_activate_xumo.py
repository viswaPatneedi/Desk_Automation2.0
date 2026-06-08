"""
Automated XUMO Device Activation Script
Follows the exact activation flow:
1. Fetch activation code from device via SSH
2. Enter activation code and check checkbox
3. Click Continue
4. Enter email/username
5. Click Continue
6. Enter password
7. Select XUMO to login

Platform Support:
- ARM64/aarch64 (Raspberry Pi) - Uses Firefox/Geckodriver
- x86_64 (Cloud/Desktop) - Uses Chrome/ChromeDriver
- Automatic browser detection and fallback handling
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys
import platform
import subprocess
import shutil
import os

# Import activation code fetcher
try:
    from method_fetch_activation_code import fetch_xumo_activation_code
except ImportError:
    print("⚠️  Warning: method_fetch_activation_code.py not found")
    print("   Using fallback static activation code")
    fetch_xumo_activation_code = None

# Default activation details (will be overridden by device fetch)
ACTIVATION_URL = "https://www.xumo.com/activate?execution=e1s1"
ACTIVATION_CODE = None  # Will be fetched from device
USERNAME = "vpatne290@cable.comcast.com"
PASSWORD = "Payansh!11302021"
DEVICE_IP = None  # Must be provided as command line argument


def detect_platform_and_browser():
    """
    Detect system architecture and available browsers.
    Returns tuple: (architecture, browser_type, browser_path, driver_available)
    
    Supports:
    - ARM64: Firefox (geckodriver)
    - x86_64: Chrome/Chromium (chromedriver)
    """
    arch = platform.machine().lower()
    system = platform.system().lower()
    
    print(f"🔍 Detected platform: {system} / {arch}")
    
    # Check for available browsers
    browsers = {
        'chrome': shutil.which('google-chrome') or shutil.which('chrome'),
        'chromium': shutil.which('chromium-browser') or shutil.which('chromium'),
        'firefox': shutil.which('firefox') or shutil.which('firefox-esr')
    }
    
    available = {k: v for k, v in browsers.items() if v}
    
    if not available:
        return arch, None, None, False
    
    # ARM64 preference: Firefox > Chromium
    if 'arm' in arch or 'aarch64' in arch:
        if 'firefox' in available:
            return arch, 'firefox', available['firefox'], True
        elif 'chromium' in available:
            return arch, 'chromium', available['chromium'], True
    
    # x86_64 preference: Chrome > Chromium > Firefox
    if 'chrome' in available:
        return arch, 'chrome', available['chrome'], True
    elif 'chromium' in available:
        return arch, 'chromium', available['chromium'], True
    elif 'firefox' in available:
        return arch, 'firefox', available['firefox'], True
    
    return arch, None, None, False


def setup_driver():
    """
    Setup WebDriver with automatic browser detection.
    Supports Chrome, Chromium, and Firefox with proper error handling.
    """
    arch, browser_type, browser_path, driver_available = detect_platform_and_browser()
    
    if not driver_available:
        raise Exception(
            "❌ No supported browser found!\n"
            "   Please install one of: Chrome, Chromium, or Firefox\n"
            f"   Platform: {arch}\n"
            "   ARM64: sudo apt install firefox-esr\n"
            "   x86_64: sudo apt install chromium-browser or google-chrome-stable"
        )
    
    print(f"🔧 Setting up {browser_type.title()} driver...")
    print(f"   Browser path: {browser_path}")
    
    try:
        if browser_type == 'firefox':
            return setup_firefox_driver()
        else:  # chrome or chromium
            return setup_chrome_driver(browser_type, browser_path)
    except Exception as e:
        print(f"❌ Failed to setup {browser_type}: {str(e)}")
        # Try fallback to Firefox if Chrome fails
        if browser_type != 'firefox' and shutil.which('firefox'):
            print("🔄 Falling back to Firefox...")
            return setup_firefox_driver()
        raise


def setup_firefox_driver():
    """Setup Firefox with geckodriver (better ARM support)"""
    try:
        from selenium.webdriver.firefox.service import Service as FirefoxService
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        
        firefox_options = FirefoxOptions()
        # firefox_options.add_argument("--headless")  # Uncomment for headless mode
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference('useAutomationExtension', False)
        
        # Try to find geckodriver in multiple locations
        geckodriver_paths = [
            os.path.expanduser("~/.local/bin/geckodriver"),  # Manual install location
            "/usr/local/bin/geckodriver",
            "/usr/bin/geckodriver",
            shutil.which("geckodriver")  # System PATH
        ]
        
        geckodriver_path = None
        for path in geckodriver_paths:
            if path and os.path.exists(path) and os.access(path, os.X_OK):
                # Verify it's the correct architecture by trying to execute it
                try:
                    result = subprocess.run([path, "--version"], 
                                          capture_output=True, 
                                          text=True, 
                                          timeout=5)
                    if result.returncode == 0:
                        geckodriver_path = path
                        print(f"   Using geckodriver: {path}")
                        break
                except (OSError, subprocess.TimeoutExpired):
                    continue
        
        if not geckodriver_path:
            # Try webdriver-manager as fallback (may fail on ARM)
            try:
                from webdriver_manager.firefox import GeckoDriverManager
                geckodriver_path = GeckoDriverManager().install()
                print(f"   Downloaded geckodriver via webdriver-manager")
            except Exception as wdm_error:
                raise Exception(
                    f"No compatible geckodriver found!\n"
                    f"   Install manually for ARM64:\n"
                    f"   mkdir -p ~/.local/bin\n"
                    f"   cd ~/.local/bin\n"
                    f"   wget https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux-aarch64.tar.gz\n"
                    f"   tar -xzf geckodriver-v0.35.0-linux-aarch64.tar.gz\n"
                    f"   chmod +x geckodriver\n"
                    f"   WebDriver Manager error: {str(wdm_error)}"
                )
        
        service = FirefoxService(geckodriver_path)
        driver = webdriver.Firefox(service=service, options=firefox_options)
        driver.maximize_window()
        print("   ✅ Firefox driver ready")
        return driver
        
    except ImportError as e:
        raise Exception(f"Firefox driver dependencies missing. Install with: pip install selenium webdriver-manager")
    except Exception as e:
        raise Exception(f"Failed to initialize Firefox driver: {str(e)}")


def setup_chrome_driver(browser_type, browser_path):
    """Setup Chrome/Chromium with chromedriver"""
    try:
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.core.os_manager import ChromeType
        
        chrome_options = ChromeOptions()
        if browser_type == 'chromium':
            chrome_options.binary_location = browser_path
        
        # chrome_options.add_argument("--headless")  # Uncomment for headless mode
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use CHROMIUM type for chromium browser
        if browser_type == 'chromium':
            service = ChromeService(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        else:
            service = ChromeService(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("   ✅ Chrome driver ready")
        return driver
        
    except Exception as e:
        # Check if it's an architecture mismatch
        if "Exec format error" in str(e) or "cannot execute binary file" in str(e):
            arch = platform.machine()
            raise Exception(
                f"❌ ChromeDriver architecture mismatch!\n"
                f"   System: {arch}\n"
                f"   ChromeDriver downloaded for wrong architecture.\n"
                f"   ARM systems should use Firefox instead.\n"
                f"   Install Firefox: sudo apt install firefox-esr"
            )
        raise Exception(f"Failed to initialize Chrome driver: {str(e)}")

def wait_and_find_element(driver, wait_time, *selectors):
    """Try multiple selectors to find an element"""
    for by_type, selector in selectors:
        try:
            element = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((by_type, selector))
            )
            return element
        except:
            continue
    return None

def wait_and_click_element(driver, wait_time, *selectors):
    """Try multiple selectors to find and click an element"""
    for by_type, selector in selectors:
        try:
            element = WebDriverWait(driver, wait_time).until(
                EC.element_to_be_clickable((by_type, selector))
            )
            element.click()
            return True
        except:
            continue
    return False


def activate_xumo_device(device_ip=None, activation_code=None):
    """Automate XUMO device activation with step-by-step flow
    
    Args:
        device_ip: IP address of XUMO device to fetch activation code from
        activation_code: Optional pre-fetched activation code (overrides device fetch)
        
    Returns:
        bool: True if activation completed successfully, False otherwise
    """
    driver = None
    success = False
    error_messages = []
    
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
                    error_msg = f"Failed to fetch activation code: {result['message']}"
                    print(f"\n❌ {error_msg}")
                    print("\n⚠️  Please provide activation code manually or check device connectivity")
                    error_messages.append(error_msg)
                    return False
            else:
                error_msg = "Activation code fetcher not available (method_fetch_activation_code.py missing)"
                print(f"\n❌ {error_msg}")
                error_messages.append(error_msg)
                return False
                
        elif not activation_code:
            error_msg = "No activation code provided and no device IP specified"
            print(f"\n❌ ERROR: {error_msg}")
            print("\nUsage:")
            print("  python auto_activate_xumo.py <device_ip>")
            print("  OR")
            print("  python auto_activate_xumo.py --code <activation_code>")
            error_messages.append(error_msg)
            return False
        
        print("\n" + "=" * 70)
        print("AUTOMATED XUMO DEVICE ACTIVATION")
        print("=" * 70)
        print(f"📱 Activation Code: {activation_code}")
        print(f"👤 Username: {USERNAME}")
        print(f"🌐 URL: {ACTIVATION_URL}")
        print("=" * 70)
        
        # Setup driver with error handling
        try:
            driver = setup_driver()
        except Exception as driver_error:
            error_msg = f"Failed to setup browser driver: {str(driver_error)}"
            print(f"\n❌ {error_msg}")
            error_messages.append(error_msg)
            
            # Provide helpful suggestions
            arch = platform.machine()
            if 'arm' in arch.lower() or 'aarch64' in arch.lower():
                print("\n💡 Solution for ARM/Raspberry Pi:")
                print("   sudo apt update")
                print("   sudo apt install firefox-esr")
                print("   pip install selenium webdriver-manager")
            else:
                print("\n💡 Solution for x86_64/Cloud:")
                print("   sudo apt update")
                print("   sudo apt install chromium-browser")
                print("   pip install selenium webdriver-manager")
            
            return False
        
        # STEP 1: Open activation page
        print("\n[STEP 1/6] 🌐 Opening activation page...")
        driver.get(ACTIVATION_URL)
        time.sleep(5)  # Wait for page to fully load
        print("     ✅ Page loaded")
        
        # STEP 2: Enter activation code
        print("\n[STEP 2/6] 📝 Entering activation code...")
        time.sleep(2)  # Additional wait for dynamic content
        
        code_input = wait_and_find_element(driver, 15,
            (By.CSS_SELECTOR, "input[placeholder='Enter your code']"),
            (By.XPATH, "//input[@placeholder='Enter your code']"),
            (By.NAME, "code"),
            (By.ID, "activationCode"),
            (By.NAME, "activationCode"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.CSS_SELECTOR, "input[placeholder*='code' i]"),
            (By.XPATH, "//input[@type='text']"),
        )
        
        if code_input:
            try:
                # Click the field first to activate it
                code_input.click()
                time.sleep(0.5)
                # Try to clear, but don't fail if it can't be cleared
                try:
                    code_input.clear()
                except:
                    pass
                code_input.send_keys(activation_code)
                print(f"     ✅ Entered code: {activation_code}")
                time.sleep(1)
            except Exception as e:
                print(f"     ⚠️  Error entering code: {e}")
                print("     Trying alternative method...")
                # Try JavaScript fallback
                try:
                    driver.execute_script(f"arguments[0].value = '{activation_code}';", code_input)
                    print(f"     ✅ Entered code via JavaScript: {activation_code}")
                    time.sleep(1)
                except Exception as js_error:
                    print(f"     ❌ JavaScript also failed: {js_error}")
                    print("     Please enter the code manually")
                    time.sleep(10)
        else:
            print("     ❌ Could not find activation code input field")
            print("     Please enter the code manually")
            time.sleep(10)
        
        # STEP 3: Check the checkbox
        print("\n[STEP 3/6] ☑️  Checking the checkbox...")
        checkbox = wait_and_find_element(driver, 5,
            (By.CSS_SELECTOR, "input[type='checkbox']"),
            (By.XPATH, "//input[@type='checkbox']"),
            (By.CSS_SELECTOR, "label input[type='checkbox']"),
            (By.XPATH, "//label//input[@type='checkbox']"),
        )
        
        if checkbox:
            try:
                # Try clicking the checkbox directly
                if not checkbox.is_selected():
                    checkbox.click()
                    print("     ✅ Checkbox checked")
            except Exception as e:
                # If direct click fails, try JavaScript
                try:
                    driver.execute_script("arguments[0].checked = true; arguments[0].click();", checkbox)
                    print("     ✅ Checkbox checked (via JavaScript)")
                except Exception as js_error:
                    print(f"     ⚠️  Could not check checkbox: {str(js_error)}")
                    print("     Please check the checkbox manually")
                    time.sleep(5)
            time.sleep(1)
        else:
            print("     ⚠️  Could not find checkbox automatically")
            print("     Please check the checkbox manually if required")
            time.sleep(5)
        
        # STEP 4: Click Continue button (first time)
        print("\n[STEP 4/6] 🔘 Clicking Continue button...")
        continue_clicked = wait_and_click_element(driver, 5,
            (By.XPATH, "//button[contains(text(), 'Continue')]"),
            (By.XPATH, "//button[contains(text(), 'CONTINUE')]"),
            (By.XPATH, "//input[@value='Continue']"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.CSS_SELECTOR, ".btn-continue"),
            (By.CSS_SELECTOR, ".continue-btn"),
        )
        
        if continue_clicked:
            print("     ✅ Clicked Continue")
            time.sleep(3)  # Wait for redirect
        else:
            print("     ❌ Could not find Continue button")
            print("     Please click Continue manually")
            time.sleep(10)
        
        # STEP 5: Enter username/email
        print("\n[STEP 5/6] 👤 Entering email/username...")
        time.sleep(3)  # Wait for page transition
        
        username_input = wait_and_find_element(driver, 10,
            (By.ID, "username"),
            (By.ID, "email"),
            (By.NAME, "username"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[name='username']"),
            (By.CSS_SELECTOR, "input[placeholder*='email' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='username' i]"),
            (By.XPATH, "//input[@type='email']"),
            (By.XPATH, "//input[@type='text' and contains(@placeholder, 'mail')]"),
        )
        
        if username_input:
            try:
                # Click the field first to make it active
                username_input.click()
                time.sleep(0.5)
                # Try to clear, but don't fail if it can't be cleared
                try:
                    username_input.clear()
                except:
                    pass
                username_input.send_keys(USERNAME)
                print(f"     ✅ Entered username: {USERNAME}")
                time.sleep(1)
            except Exception as e:
                print(f"     ⚠️  Error entering username: {e}")
                print("     Trying alternative method...")
                # Try JavaScript as alternative
                try:
                    driver.execute_script(f"arguments[0].value = '{USERNAME}';", username_input)
                    print(f"     ✅ Entered username via JavaScript: {USERNAME}")
                except:
                    print("     ❌ Could not enter username automatically")
                    print("     Please enter the email manually")
                    time.sleep(10)
        else:
            print("     ❌ Could not find username/email input field")
            print("     Please enter the email manually")
            time.sleep(10)
        
        # Click "Continue with Xumo" button (after username)
        print("\n[STEP 5.5/6] 🔘 Clicking 'Continue with Xumo' button...")
        
        # Look specifically for "Continue with Xumo" button
        continue_clicked = wait_and_click_element(driver, 8,
            (By.XPATH, "//button[contains(text(), 'Continue with Xumo')]"),
            (By.XPATH, "//button[contains(text(), 'Continue with XUMO')]"),
            (By.XPATH, "//button[normalize-space()='Continue with Xumo']"),
            (By.CSS_SELECTOR, "button[class*='xumo']"),
            (By.XPATH, "//button[contains(@class, 'xumo')]"),
            (By.XPATH, "//button[contains(text(), 'Continue')][not(contains(text(), 'Spectrum'))]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
        )
        
        if continue_clicked:
            print("     ✅ Clicked Continue")
            time.sleep(3)  # Wait for redirect to password page
        else:
            print("     ⚠️  Could not find Continue button")
            print("     Please click Continue manually")
            time.sleep(10)
        
        # STEP 6: Enter password
        print("\n[STEP 6/6] 🔑 Entering password...")
        time.sleep(3)  # Wait for page transition
        
        password_input = wait_and_find_element(driver, 10,
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//input[@type='password']"),
        )
        
        if password_input:
            try:
                # Click the field first to make it active
                password_input.click()
                time.sleep(0.5)
                # Try to clear, but don't fail if it can't be cleared
                try:
                    password_input.clear()
                except:
                    pass
                password_input.send_keys(PASSWORD)
                print("     ✅ Entered password: ********")
                time.sleep(1)
            except Exception as e:
                print(f"     ⚠️  Error entering password: {e}")
                print("     Trying alternative method...")
                # Try JavaScript as alternative
                try:
                    driver.execute_script(f"arguments[0].value = '{PASSWORD}';", password_input)
                    print("     ✅ Entered password via JavaScript: ********")
                except:
                    print("     ❌ Could not enter password automatically")
                    print("     Please enter the password manually")
                    time.sleep(10)
        else:
            print("     ❌ Could not find password input field")
            print("     Please enter the password manually")
            time.sleep(10)
        
        # STEP 7: Click Sign in button
        print("\n[STEP 7/6] 🔐 Clicking 'Sign in' button...")
        time.sleep(2)  # Wait a moment after entering password
        
        signin_clicked = wait_and_click_element(driver, 8,
            (By.XPATH, "//button[contains(text(), 'Sign in')]"),
            (By.XPATH, "//button[contains(text(), 'Sign In')]"),
            (By.XPATH, "//button[normalize-space()='Sign in']"),
            (By.XPATH, "//button[contains(text(), 'Log in')]"),
            (By.XPATH, "//button[contains(text(), 'Log In')]"),
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//input[@type='submit']"),
        )
        
        if signin_clicked:
            print("     ✅ Clicked Sign in button")
            time.sleep(3)  # Wait for login to complete
        else:
            print("     ⚠️  Could not find Sign in button automatically")
            print("     Please click Sign in manually")
            time.sleep(10)
        
        print("\n" + "=" * 70)
        print("✅ AUTOMATION COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\n📺 The browser will remain open for 60 seconds.")
        print("   Please verify the activation was successful.")
        print("\n💡 If any step failed, you can complete it manually in the browser.")
        print("=" * 70)
        
        success = True
        
        # Wait to see results
        time.sleep(60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Activation interrupted by user (Ctrl+C)")
        error_messages.append("User interrupted activation")
        return False
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ UNEXPECTED ERROR: {error_msg}")
        error_messages.append(error_msg)
        
        import traceback
        print("\n📋 Full error details:")
        traceback.print_exc()
        
        print("\n⚠️  The browser will remain open for 60 seconds for manual completion.")
        time.sleep(60)
        
        return False
        
    finally:
        if driver:
            try:
                print("\n🔒 Closing browser...")
                driver.quit()
                print("✅ Browser closed")
            except:
                print("⚠️  Could not close browser cleanly")
        
        # Print final summary
        print("\n" + "=" * 70)
        if success:
            print("🎉 XUMO ACTIVATION COMPLETED SUCCESSFULLY")
        else:
            print("❌ XUMO ACTIVATION FAILED")
            if error_messages:
                print("\nErrors encountered:")
                for i, err in enumerate(error_messages, 1):
                    print(f"  {i}. {err}")
        print("=" * 70)

if __name__ == "__main__":
    # Parse command line arguments
    device_ip = None
    activation_code = None
    
    if len(sys.argv) > 1:
        # Check for --code flag
        if "--code" in sys.argv:
            code_index = sys.argv.index("--code")
            if len(sys.argv) > code_index + 1:
                activation_code = sys.argv[code_index + 1]
                print(f"Using provided activation code: {activation_code}")
        else:
            # First argument is device IP
            device_ip = sys.argv[1]
            print(f"Will fetch activation code from device: {device_ip}")
    else:
        print("\n" + "=" * 70)
        print("XUMO Device Activation Script")
        print("=" * 70)
        print("\nUsage:")
        print("  1. Fetch code from device:")
        print("     python auto_activate_xumo.py <device_ip>")
        print("     Example: python auto_activate_xumo.py 10.0.0.126")
        print("\n  2. Use manual activation code:")
        print("     python auto_activate_xumo.py --code <activation_code>")
        print("     Example: python auto_activate_xumo.py --code 679534")
        print("\n" + "=" * 70)
        sys.exit(1)
    
    activate_xumo_device(device_ip=device_ip, activation_code=activation_code)
