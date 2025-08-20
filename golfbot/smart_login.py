from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Dict, List, Optional, Tuple, Any

from rich.console import Console
from playwright.async_api import Page, Locator

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

console = Console()


class LoginStrategy:
    """Base class for login strategies"""
    
    def __init__(self, name: str):
        self.name = name
    
    async def attempt_login(self, page: Page, username: str, password: str) -> Tuple[bool, str]:
        """Returns (success, message)"""
        raise NotImplementedError





class HeuristicStrategy(LoginStrategy):
    """Smart heuristic analysis of the page"""
    
    def __init__(self):
        super().__init__("Heuristic Analysis")
    
    async def attempt_login(self, page: Page, username: str, password: str) -> Tuple[bool, str]:
        try:
            # Get all form elements
            inputs = await page.query_selector_all("input")
            buttons = await page.query_selector_all("button, input[type='submit']")
            
            console.print(f"[dim]Found {len(inputs)} inputs, {len(buttons)} buttons[/dim]")
            
            # Analyze inputs
            username_candidates = []
            password_candidates = []
            
            for input_elem in inputs:
                input_type = await input_elem.get_attribute("type") or "text"
                input_name = await input_elem.get_attribute("name") or ""
                input_id = await input_elem.get_attribute("id") or ""
                input_placeholder = await input_elem.get_attribute("placeholder") or ""
                
                # Check visibility
                is_visible = await input_elem.is_visible()
                if not is_visible:
                    continue
                
                element_text = f"type={input_type} name={input_name} id={input_id} placeholder={input_placeholder}"
                
                # Username field detection
                if (input_type in ["email", "text"] or 
                    any(keyword in input_name.lower() for keyword in ["user", "email", "login", "brukernavn"]) or
                    any(keyword in input_id.lower() for keyword in ["user", "email", "login", "brukernavn"]) or
                    any(keyword in input_placeholder.lower() for keyword in ["user", "email", "brukernavn"])):
                    
                    username_candidates.append((input_elem, element_text))
                
                # Password field detection
                if (input_type == "password" or
                    any(keyword in input_name.lower() for keyword in ["pass", "pwd"]) or
                    any(keyword in input_id.lower() for keyword in ["pass", "pwd"]) or
                    any(keyword in input_placeholder.lower() for keyword in ["pass", "pwd"])):
                    
                    password_candidates.append((input_elem, element_text))
            
            console.print(f"[dim]Username candidates: {len(username_candidates)}, Password candidates: {len(password_candidates)}[/dim]")
            
            if not username_candidates or not password_candidates:
                return False, "Could not identify username/password fields"
            
            # Use first candidates
            username_elem = username_candidates[0][0]
            password_elem = password_candidates[0][0]
            
            console.print(f"[cyan]Selected username: {username_candidates[0][1]}[/cyan]")
            console.print(f"[cyan]Selected password: {password_candidates[0][1]}[/cyan]")
            
            # Fill fields with validation
            await username_elem.fill(username)
            filled_username = await username_elem.input_value()
            if filled_username == username:
                console.print(f"[green]✓ Username filled correctly: '{username}'[/green]")
            else:
                console.print(f"[red]⚠️ Username mismatch! Expected: '{username}', Got: '{filled_username}'[/red]")
            
            await password_elem.fill(password)
            filled_password = await password_elem.input_value()
            if len(filled_password) == len(password):
                console.print("[green]✓ Password filled correctly[/green]")
            else:
                console.print(f"[red]⚠️ Password length mismatch! Expected: {len(password)}, Got: {len(filled_password)}[/red]")
            
            # Find submit button
            submit_elem = None
            for button in buttons:
                button_text = await button.text_content() or ""
                button_type = await button.get_attribute("type") or ""
                
                if (button_type == "submit" or
                    any(keyword in button_text.lower() for keyword in ["login", "sign in", "logg inn", "submit"])):
                    submit_elem = button
                    break
            
            if submit_elem:
                await submit_elem.click()
                console.print("[green]✓ Submit button clicked[/green]")
            else:
                await password_elem.press("Enter")
                console.print("[green]✓ Enter pressed on password field[/green]")
            
            return True, "Heuristic analysis successful"
            
        except Exception as e:
            return False, f"Heuristic analysis failed: {e}"


class AIStrategy(LoginStrategy):
    """Enhanced AI-powered login with better prompts"""
    
    def __init__(self):
        super().__init__("AI Analysis")
    
    async def _get_page_analysis(self, page: Page) -> Dict[str, Any]:
        """Get comprehensive page analysis"""
        script = """
        () => {
            function getElementInfo(el) {
                const rect = el.getBoundingClientRect();
                const styles = window.getComputedStyle(el);
                
                return {
                    tag: el.tagName.toLowerCase(),
                    type: el.type || null,
                    id: el.id || null,
                    name: el.name || null,
                    className: el.className || null,
                    placeholder: el.placeholder || null,
                    value: el.value || null,
                    text: (el.innerText || el.textContent || '').trim().slice(0, 100),
                    visible: rect.width > 0 && rect.height > 0 && styles.visibility !== 'hidden' && styles.display !== 'none',
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                };
            }
            
            const inputs = Array.from(document.querySelectorAll('input'))
                .map(getElementInfo)
                .filter(info => info.visible);
                
            const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], a[role="button"]'))
                .map(getElementInfo)
                .filter(info => info.visible);
                
            const forms = Array.from(document.querySelectorAll('form'))
                .map(form => ({
                    action: form.action || null,
                    method: form.method || null,
                    id: form.id || null,
                    className: form.className || null
                }));
            
            return {
                url: window.location.href,
                title: document.title,
                inputs: inputs,
                buttons: buttons,
                forms: forms,
                bodyText: document.body.innerText.slice(0, 1000)
            };
        }
        """
        
        try:
            return await page.evaluate(script)
        except Exception:
            return {"inputs": [], "buttons": [], "forms": []}
    
    async def _call_ai(self, page_analysis: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Call AI with enhanced analysis"""
        if not OpenAI or not os.getenv("OPENAI_API_KEY"):
            return None
        
        prompt = f"""You are analyzing a Norwegian golf booking website login page. Based on the comprehensive page analysis below, identify the exact CSS selectors for the login form.

PAGE ANALYSIS:
URL: {page_analysis.get('url', 'unknown')}
Title: {page_analysis.get('title', 'unknown')}

VISIBLE INPUTS:
{json.dumps(page_analysis.get('inputs', []), indent=2)}

VISIBLE BUTTONS:
{json.dumps(page_analysis.get('buttons', []), indent=2)}

FORMS:
{json.dumps(page_analysis.get('forms', []), indent=2)}

PAGE TEXT SAMPLE:
{page_analysis.get('bodyText', '')[:500]}

TASK: Return CSS selectors for username, password, and submit elements.

RULES:
1. Return ONLY valid CSS selectors (no :contains, no comma-separated lists)
2. Prefer specific IDs when available
3. Look for Norwegian text: "Brukernavn", "Passord", "Logg inn"
4. Username: typically input[type="email"] or input[type="text"] with user-related names
5. Password: typically input[type="password"]
6. Submit: button with login text or input[type="submit"]

Return JSON format:
{{"username": "CSS_SELECTOR", "password": "CSS_SELECTOR", "submit": "CSS_SELECTOR"}}

Examples:
{{"username": "#gbLoginUsername", "password": "#gbLoginPassword", "submit": "button.login-btn"}}
{{"username": "input[name='email']", "password": "input[type='password']", "submit": "button[type='submit']"}}
"""

        try:
            client = OpenAI()
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a web automation expert. Return only valid JSON with CSS selectors."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            content = response.choices[0].message.content or ""
            console.print(f"[dim]AI Response: {content[:200]}...[/dim]")
            
            # Extract JSON
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
                
        except Exception as e:
            console.print(f"[red]AI call failed: {e}[/red]")
        
        return None
    
    async def attempt_login(self, page: Page, username: str, password: str) -> Tuple[bool, str]:
        try:
            # Get comprehensive page analysis
            analysis = await self._get_page_analysis(page)
            console.print(f"[dim]Page analysis: {len(analysis.get('inputs', []))} inputs, {len(analysis.get('buttons', []))} buttons[/dim]")
            
            # Get AI recommendation
            selectors = await self._call_ai(analysis)
            if not selectors:
                return False, "AI analysis failed"
            
            console.print(f"[cyan]AI selected: {selectors}[/cyan]")
            
            # Validate and execute
            for field, selector in selectors.items():
                try:
                    count = await page.locator(selector).count()
                    console.print(f"[dim]{field}: {selector} -> {count} elements[/dim]")
                    if count == 0:
                        return False, f"AI selector for {field} found no elements"
                except Exception:
                    return False, f"Invalid AI selector for {field}: {selector}"
            
            # Execute login with validation
            await page.fill(selectors["username"], username)
            filled_username = await page.locator(selectors["username"]).input_value()
            if filled_username == username:
                console.print(f"[green]✓ Username filled correctly (AI): '{username}'[/green]")
            else:
                console.print(f"[red]⚠️ Username mismatch (AI)! Expected: '{username}', Got: '{filled_username}'[/red]")
            
            await page.fill(selectors["password"], password)
            filled_password = await page.locator(selectors["password"]).input_value()
            if len(filled_password) == len(password):
                console.print("[green]✓ Password filled correctly (AI)[/green]")
            else:
                console.print(f"[red]⚠️ Password length mismatch (AI)! Expected: {len(password)}, Got: {len(filled_password)}[/red]")
            
            await page.locator(selectors["submit"]).first.click()
            console.print("[green]✓ Submit clicked (AI)[/green]")
            
            return True, "AI strategy successful"
            
        except Exception as e:
            return False, f"AI strategy failed: {e}"


class SmartLogin:
    """Orchestrates multiple login strategies"""
    
    def __init__(self):
        self.strategies = [
            HeuristicStrategy(),
            AIStrategy(),
        ]
    
    async def attempt_login(self, page: Page, username: str, password: str, debug: bool = True) -> bool:
        """Try all strategies until one succeeds"""
        
        console.print("[bold cyan]🤖 Starting Smart Login System[/bold cyan]")
        
        # Check if we're on an error page first
        current_url = page.url.lower()
        if "login/help.asp" in current_url or "portal/login/help" in current_url:
            console.print(f"[red]❌ Redirected to login help page - credentials may be incorrect: {page.url}[/red]")
            console.print("[red]This usually means 'User not found' - check your GOLFBOX_USER and GOLFBOX_PASS[/red]")
            return False
        
        # Validate URL - attempt login from golfbox.golf or norskgolf.no
        if "golfbox.golf" not in current_url and "norskgolf.no" not in current_url and "golfbox.no" not in current_url:
            console.print(f"[red]❌ Not on a supported login page. Current URL: {page.url}[/red]")
            return False
        
        if "norskgolf.no" in current_url:
            console.print(f"[yellow]⚠️ On norskgolf.no - will handle login popup[/yellow]")
        elif "golfbox.no" in current_url:
            console.print(f"[yellow]⚠️ On golfbox.no - will handle login form[/yellow]")
        
        # Validate credentials
        if not username or not password:
            console.print("[red]❌ Username or password is empty[/red]")
            return False
        
        # Mask password for logging and validate format
        masked_password = password[:2] + "*" * (len(password) - 2) if len(password) > 2 else "***"
        console.print(f"[dim]Using credentials: username='{username}', password='{masked_password}'[/dim]")
        
        # Basic credential validation
        if "@" not in username and len(username) < 3:
            console.print("[yellow]⚠️ Username seems short - make sure it's correct[/yellow]")
        if len(password) < 4:
            console.print("[yellow]⚠️ Password seems short - make sure it's correct[/yellow]")
        
        # Pre-login setup
        await self._prepare_page(page)
        
        for strategy in self.strategies:
            console.print(f"\n[bold blue]Trying: {strategy.name}[/bold blue]")
            
            try:
                success, message = await strategy.attempt_login(page, username, password)
                
                if success:
                    console.print(f"[bold green]✅ {strategy.name} succeeded: {message}[/bold green]")
                    
                    # Wait for navigation and verify
                    await asyncio.sleep(2)
                    if await self._verify_login_success(page):
                        console.print("[bold green]🎉 Login verified successful![/bold green]")
                        return True
                    else:
                        console.print("[yellow]⚠️ Login appeared to succeed but verification failed[/yellow]")
                else:
                    console.print(f"[red]❌ {strategy.name} failed: {message}[/red]")
                    
            except Exception as e:
                console.print(f"[red]💥 {strategy.name} crashed: {e}[/red]")
                continue
        
        console.print("[bold red]🚫 All login strategies failed[/bold red]")
        return False
    
    async def _prepare_page(self, page: Page):
        """Prepare page for login attempts"""
        try:
            current_url = page.url.lower()
            
            # Handle cookie banners
            cookie_selectors = [
                "button:has-text('Godta')",
                "button:has-text('Accept')",
                "button:has-text('Aksepter')",
                "#onetrust-accept-btn-handler"
            ]
            
            for selector in cookie_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        await page.locator(selector).first.click()
                        await asyncio.sleep(0.5)
                        console.print("[dim]Cookie banner handled[/dim]")
                        break
                except:
                    continue
            
            # Special handling for norskgolf.no - trigger the golfbox login popup
            if "norskgolf.no" in current_url:
                console.print("[cyan]Handling norskgolf.no login popup...[/cyan]")
                
                # Look for golfbox login triggers on norskgolf.no
                norskgolf_triggers = [
                    "a:has-text('Logg inn med Golfbox')",
                    "button:has-text('Logg inn med Golfbox')",
                    "a[href*='golfbox']",
                    ".golfbox-login",
                    "#golfbox-login",
                    "a:contains('Golfbox')",
                    "button:contains('Golfbox')",
                    # Look for any login link that might open the popup
                    "a:has-text('Logg inn')",
                    "button:has-text('Logg inn')",
                ]
                
                popup_opened = False
                for trigger in norskgolf_triggers:
                    try:
                        if await page.locator(trigger).count() > 0:
                            console.print(f"[dim]Trying norskgolf trigger: {trigger}[/dim]")
                            
                            # Set up popup handler before clicking
                            popup = None
                            try:
                                async with page.expect_popup(timeout=3000) as popup_info:
                                    await page.locator(trigger).first.click()
                                    popup = await popup_info.value
                                    console.print("[green]✓ Login popup opened[/green]")
                                    popup_opened = True
                                    
                                    # Wait for popup to load
                                    await popup.wait_for_load_state("domcontentloaded")
                                    
                                    # Replace the main page with the popup for login
                                    # This is a bit of a hack but allows the rest of the system to work
                                    page._impl_obj = popup._impl_obj
                                    break
                            except:
                                # No popup, maybe it's an inline form
                                await asyncio.sleep(1)
                                # Check if login form appeared
                                if await page.locator("input[type='password']").count() > 0:
                                    console.print("[green]✓ Login form appeared inline[/green]")
                                    popup_opened = True
                                    break
                    except Exception as e:
                        console.print(f"[dim]Trigger {trigger} failed: {e}[/dim]")
                        continue
                
                if not popup_opened:
                    console.print("[yellow]⚠️ Could not open norskgolf.no login popup[/yellow]")
                    
            else:
                # Standard golfbox.golf login triggers
                login_triggers = [
                    "a:has-text('Logg inn')",
                    "button:has-text('Logg inn')",
                    "a:has-text('Login')",
                    "button:has-text('Login')",
                    ".login-trigger",
                    "#login-btn"
                ]
                
                for trigger in login_triggers:
                    try:
                        if await page.locator(trigger).count() > 0:
                            await page.locator(trigger).first.click()
                            await asyncio.sleep(1)
                            console.print("[dim]Login trigger clicked[/dim]")
                            break
                    except:
                        continue
                    
        except Exception as e:
            console.print(f"[yellow]Page preparation warning: {e}[/yellow]")
    
    async def _verify_login_success(self, page: Page) -> bool:
        """Verify if login was successful"""
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except:
            await asyncio.sleep(2)
        
        try:
            url = page.url.lower()
            content = (await page.content()).lower()
            
            # Success indicators
            success_patterns = [
                "dashboard" in url,
                "profile" in url,
                "booking" in url,
                "starttid" in url,
                "logout" in content,
                "logg ut" in content,
                "min side" in content,
                "velkommen" in content,
                "profile" in content,
            ]
            
            # Failure indicators
            failure_patterns = [
                "login" in url and "error" in url,
                "invalid" in content,
                "feil passord" in content,
                "wrong password" in content,
            ]
            
            if any(failure_patterns):
                return False
            
            if any(success_patterns):
                return True
            
            # If no login form is present anymore, assume success
            login_indicators = ["logg inn", "login", "sign in", "password"]
            if not any(indicator in content for indicator in login_indicators):
                return True
            
            return False
            
        except Exception:
            return True  # Assume success if we can't verify


# Main interface function
async def smart_login(page: Page, username: str, password: str, debug: bool = True) -> bool:
    """Main entry point for smart login"""
    smart_login_system = SmartLogin()
    return await smart_login_system.attempt_login(page, username, password, debug)
