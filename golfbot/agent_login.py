from __future__ import annotations

import asyncio
import json
import os
from typing import Dict, Optional

from rich.console import Console

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore


console = Console()


async def _collect_dom_candidates(page) -> Dict[str, list[dict]]:
    """Return lightweight descriptors of inputs and buttons on the page.

    Each descriptor includes: css, id, name, type, placeholder, label/text.
    """
    script = """
    () => {
      function toDesc(el) {
        const d = {
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          name: el.getAttribute('name') || null,
          type: el.getAttribute('type') || null,
          placeholder: el.getAttribute('placeholder') || null,
          aria_label: el.getAttribute('aria-label') || null,
          text: (el.innerText || el.textContent || '').trim().slice(0, 120),
        };
        // Build a simple CSS selector
        let sel = d.tag;
        if (d.id) sel += `#${d.id}`;
        const classes = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0,3);
        if (!d.id && classes.length) sel += '.' + classes.join('.');
        d.css = sel;
        return d;
      }
      const inputs = Array.from(document.querySelectorAll('input, textarea'))
        .filter(el => el.offsetParent !== null)  // visible-ish
        .map(toDesc);
      const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], a[role="button"]'))
        .filter(el => el.offsetParent !== null)
        .map(toDesc);
      return { inputs, buttons };
    }
    """
    try:
        return await page.evaluate(script)
    except Exception:
        return {"inputs": [], "buttons": []}


def _build_prompt(candidates: Dict[str, list[dict]]) -> str:
    return (
        "You are an expert web automation assistant helping to log into a Norwegian golf booking website (golfbox.golf). "
        "Analyze the provided HTML elements and identify the correct login form fields.\n\n"
        
        "TASK: Select CSS selectors for username/email field, password field, and submit button.\n\n"
        
        "GUIDELINES:\n"
        "- Look for Norwegian text like 'Brukernavn', 'E-post', 'Passord', 'Logg inn', 'Sign in'\n"
        "- Username field: input[type='email'], input[type='text'], or inputs with names like 'username', 'email', 'user', 'brukernavn'\n"
        "- Password field: input[type='password'] or names like 'password', 'passord', 'pass'\n"
        "- Submit button: button or input with text 'Logg inn', 'Sign in', 'Login', or type='submit'\n"
        "- Prefer elements with clear IDs like #username, #password, #login\n"
        "- Avoid hidden fields (type='hidden')\n"
        "- Look for form elements that are likely visible to users\n"
        "- IMPORTANT: Use valid CSS selectors only. Do NOT use :contains() - use button:has-text() for Playwright\n"
        "- IMPORTANT: Return single selectors, not comma-separated lists\n"
        "- IMPORTANT: Use specific IDs when available (e.g., #gbLoginUsername, #gbLoginPassword)\n\n"
        
        "RESPONSE FORMAT: Return ONLY valid JSON:\n"
        "{\"username_selector\": \"CSS_SELECTOR\", \"password_selector\": \"CSS_SELECTOR\", \"submit_selector\": \"CSS_SELECTOR\"}\n\n"
        
        "EXAMPLE GOOD RESPONSES:\n"
        "{\"username_selector\": \"#gbLoginUsername\", \"password_selector\": \"#gbLoginPassword\", \"submit_selector\": \"button[title='Sign in']\"}\n"
        "{\"username_selector\": \"input[name='username']\", \"password_selector\": \"input[type='password']\", \"submit_selector\": \"input[type='submit']\"}\n\n"
        
        f"HTML ELEMENTS TO ANALYZE:\n{json.dumps(candidates, indent=2)[:15000]}\n"
    )


async def _call_openai(prompt: str, attempt: int = 1) -> Optional[Dict[str, str]]:
    if OpenAI is None:
        return None
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def _sync_call() -> Optional[Dict[str, str]]:
        try:
            client = OpenAI(api_key=api_key)
            system_msg = (
                "You are a web automation expert. Analyze HTML elements and return ONLY valid JSON "
                "with CSS selectors for login form fields. Be precise and prefer unique identifiers."
            )
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0 if attempt == 1 else 0.2,  # More creative on retries
                max_tokens=500,
            )
            content = resp.choices[0].message.content or ""
            console.print(f"[dim]AI response (attempt {attempt}): {content[:200]}...[/dim]")
            
            # Multiple JSON extraction strategies
            for strategy in [
                lambda c: c[c.find("{"):c.rfind("}") + 1],  # Find outer braces
                lambda c: c[c.find('{"'):c.rfind('"}') + 2],  # Find quoted braces
                lambda c: c.split("```json")[-1].split("```")[0] if "```json" in c else c,  # Code blocks
            ]:
                try:
                    json_str = strategy(content).strip()
                    if json_str and json_str.startswith("{") and json_str.endswith("}"):
                        data = json.loads(json_str)
                        out = {
                            "username_selector": str(data.get("username_selector", "")).strip(),
                            "password_selector": str(data.get("password_selector", "")).strip(),
                            "submit_selector": str(data.get("submit_selector", "")).strip(),
                        }
                        # Validate selectors are simple and valid
                        valid = True
                        for key, selector in out.items():
                            if not selector or len(selector) < 3:
                                valid = False
                                break
                            # Check for invalid patterns
                            if any(invalid in selector for invalid in [":contains(", ", ", "input, input"]):
                                console.print(f"[red]Invalid selector pattern in {key}: {selector}[/red]")
                                valid = False
                                break
                        
                        if valid:
                            console.print(f"[green]AI extracted selectors: {out}[/green]")
                            return out
                except Exception:
                    continue
            
            console.print(f"[red]Failed to extract valid JSON from AI response[/red]")
        except Exception as e:
            console.print(f"[red]OpenAI API error: {e}[/red]")
        return None

    return await asyncio.to_thread(_sync_call)


async def ai_login(page, user: str, password: str, debug: bool = False) -> bool:
    """AI-assisted login: ask an LLM to pick selectors and perform the login.

    Returns True if we believe login succeeded.
    """
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        try:
            console.print(f"[cyan]AI login attempt {attempt}/{max_attempts}[/cyan]")
            
            # Wait a moment for page to stabilize
            await asyncio.sleep(1)
            
            # Collect DOM candidates
            cands = await _collect_dom_candidates(page)
            console.print(f"[dim]Found {len(cands.get('inputs', []))} inputs, {len(cands.get('buttons', []))} buttons[/dim]")
            
            if not cands.get("inputs") and not cands.get("buttons"):
                console.print("[yellow]No form elements found on page[/yellow]")
                continue
            
            # Get AI recommendation
            prompt = _build_prompt(cands)
            plan = await _call_openai(prompt, attempt)
            if not plan:
                console.print(f"[red]AI failed to provide selectors on attempt {attempt}[/red]")
                continue
            
            console.print(f"[cyan]AI login plan: {plan}[/cyan]")
            
            # Validate selectors exist before trying to use them
            selectors_valid = True
            for field, selector in plan.items():
                try:
                    count = await page.locator(selector).count()
                    console.print(f"[dim]{field}: {selector} -> {count} elements[/dim]")
                    if count == 0:
                        console.print(f"[yellow]Warning: {field} selector '{selector}' found no elements[/yellow]")
                        selectors_valid = False
                except Exception as e:
                    console.print(f"[red]Invalid selector {field}: {selector} - {e}[/red]")
                    selectors_valid = False
            
            if not selectors_valid and attempt < max_attempts:
                console.print("[yellow]Some selectors invalid, retrying with different AI approach[/yellow]")
                continue
            
            # Execute login sequence
            success_steps = 0
            
            # Fill username
            try:
                username_count = await page.locator(plan["username_selector"]).count()
                if username_count > 0:
                    await page.fill(plan["username_selector"], user)
                    console.print("[green]✓ Username filled[/green]")
                    success_steps += 1
                else:
                    console.print("[red]✗ Username field not found[/red]")
            except Exception as e:
                console.print(f"[red]✗ Username fill failed: {e}[/red]")
            
            # Fill password
            try:
                password_count = await page.locator(plan["password_selector"]).count()
                if password_count > 0:
                    # Check if password field is visible, if not try to make it visible
                    is_visible = await page.locator(plan["password_selector"]).is_visible()
                    if not is_visible:
                        console.print("[yellow]Password field not visible, trying to make it visible[/yellow]")
                        # Try clicking on the field or its parent to focus it
                        try:
                            await page.locator(plan["password_selector"]).click(timeout=2000)
                        except:
                            pass
                        # Wait a moment for visibility
                        await asyncio.sleep(0.5)
                    
                    await page.fill(plan["password_selector"], password)
                    console.print("[green]✓ Password filled[/green]")
                    success_steps += 1
                else:
                    console.print("[red]✗ Password field not found[/red]")
            except Exception as e:
                console.print(f"[red]✗ Password fill failed: {e}[/red]")
            
            # Submit
            try:
                # Try multiple submit approaches
                submit_success = False
                
                # First try the AI-suggested selector
                try:
                    submit_count = await page.locator(plan["submit_selector"]).count()
                    if submit_count > 0:
                        await page.locator(plan["submit_selector"]).first.click()
                        console.print("[green]✓ Submit button clicked[/green]")
                        submit_success = True
                        success_steps += 1
                except Exception as e:
                    console.print(f"[yellow]AI submit selector failed: {e}[/yellow]")
                
                # Fallback: try common submit selectors
                if not submit_success:
                    fallback_selectors = [
                        "button:has-text('Logg inn')",
                        "button:has-text('Sign in')",
                        "input[type='submit']",
                        "button[type='submit']",
                        ".ngfGbModal-login-button",
                        "#login-button",
                        "button.login",
                    ]
                    
                    for fallback in fallback_selectors:
                        try:
                            if await page.locator(fallback).count() > 0:
                                await page.locator(fallback).first.click()
                                console.print(f"[green]✓ Submit via fallback: {fallback}[/green]")
                                submit_success = True
                                success_steps += 1
                                break
                        except Exception:
                            continue
                
                # Last resort: press Enter on password field
                if not submit_success:
                    try:
                        await page.locator(plan["password_selector"]).press("Enter")
                        console.print("[green]✓ Submit via Enter key[/green]")
                        success_steps += 1
                    except Exception:
                        console.print("[red]✗ All submit methods failed[/red]")
                        
            except Exception as e:
                console.print(f"[red]✗ Submit failed: {e}[/red]")
            
            if success_steps < 2:  # Need at least username/password filled
                console.print(f"[red]Insufficient success steps ({success_steps}/3), trying next attempt[/red]")
                continue
            
            # Wait for navigation/response
            console.print("[dim]Waiting for page response...[/dim]")
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                await asyncio.sleep(2)  # Fallback wait
            
            # Check for success indicators
            try:
                current_url = page.url.lower()
                page_text = (await page.content()).lower()
                
                # Success indicators
                success_indicators = [
                    "dashboard" in current_url,
                    "profile" in current_url,
                    "booking" in current_url,
                    "starttid" in current_url,
                    "logout" in page_text,
                    "logg ut" in page_text,
                    "min side" in page_text,
                    "velkommen" in page_text,
                ]
                
                # Failure indicators
                failure_indicators = [
                    "login" in current_url and "error" in current_url,
                    "invalid" in page_text,
                    "feil" in page_text,
                    "wrong" in page_text,
                ]
                
                if any(success_indicators):
                    console.print("[green]✓ Login appears successful![/green]")
                    return True
                elif any(failure_indicators):
                    console.print("[red]✗ Login appears to have failed[/red]")
                elif not any(k in page_text for k in ["logg inn", "login", "sign in"]):
                    console.print("[green]✓ Login keywords no longer present - likely successful[/green]")
                    return True
                else:
                    console.print("[yellow]Login result unclear, checking next attempt[/yellow]")
                    
            except Exception as e:
                console.print(f"[yellow]Could not verify login success: {e}[/yellow]")
                return True  # Assume success if we can't check
                
        except Exception as e:
            console.print(f"[red]AI login attempt {attempt} failed: {e}[/red]")
            continue
    
    console.print(f"[red]All {max_attempts} AI login attempts failed[/red]")
    return False


