"""
YouTube Tutorial AI Agent - Command Line Interface (CLI).
Interactive terminal tool for developers to query YouTube video tutorials.
"""

import sys
import argparse
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from yt_agent.agent import YouTubeTutorialAgent
from yt_agent.config import GROQ_API_KEY, OPENAI_API_KEY, DEFAULT_GROQ_MODEL, DEFAULT_OPENAI_MODEL

# Safe UTF-8 reconfiguration for Windows console environments
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)



def print_banner():
    console.print(
        Panel.fit(
            "[bold cyan]🎓 Awais(YT) Ai Agent[/bold cyan]\n"
            "[dim]Turn any YouTube tutorial into timestamped explanations, code & study guides[/dim]",
            border_style="cyan"
        )
    )


def interactive_chat(agent: YouTubeTutorialAgent):
    """Runs a multi-turn terminal chat session."""
    console.print("\n[bold green]💬 Interactive Chat Mode Started![/bold green]")
    console.print("[dim]Type your question and press Enter. Type 'exit' or 'quit' to end.[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold yellow]You[/bold yellow]")
            if not user_input.strip():
                continue
            if user_input.strip().lower() in ["exit", "quit", "q"]:
                console.print("[bold cyan]Goodbye! Happy coding![/bold cyan]")
                break

            console.print("\n[bold blue]🤖 Agent Thinking & Generating...[/bold blue]\n")
            
            # Streaming output
            collected = []
            for chunk in agent.chat(user_input, stream=True):
                sys.stdout.write(chunk)
                sys.stdout.flush()
                collected.append(chunk)
            console.print("\n")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold cyan]Session closed. Goodbye![/bold cyan]")
            break


def main():
    parser = argparse.ArgumentParser(description="YouTube Tutorial AI Agent CLI")
    parser.add_argument("--url", "-u", type=str, help="YouTube video URL or Video ID")
    parser.add_argument(
        "--provider", "-p",
        type=str,
        default="groq",
        choices=["groq", "openai"],
        help="LLM Provider: groq (default) or openai"
    )
    parser.add_argument("--model", "-m", type=str, default=None, help="Specific LLM Model name")
    parser.add_argument("--api-key", "-k", type=str, default=None, help="Provider API key")
    parser.add_argument(
        "--mode",
        choices=["chat", "curriculum", "code", "notes", "quiz", "factcheck", "pdf"],
        default="chat",
        help="Execution mode (default: chat)"
    )

    args = parser.parse_args()
    print_banner()

    # Determine API key
    api_key = args.api_key
    if not api_key:
        api_key = GROQ_API_KEY if args.provider == "groq" else OPENAI_API_KEY

    if not api_key:
        console.print(
            f"[bold red]Error:[/bold red] Missing {args.provider.upper()}_API_KEY.\n"
            "Please provide --api-key <KEY> or set it in your .env file."
        )
        sys.exit(1)

    url = args.url
    if not url:
        url = Prompt.ask("[bold green]Enter YouTube Tutorial URL[/bold green]")

    console.print(f"[dim]Connecting to {args.provider.upper()} and extracting video transcript...[/dim]")
    try:
        agent = YouTubeTutorialAgent(
            provider=args.provider,
            api_key=api_key,
            model=args.model
        )
        info = agent.load_video(url)

        console.print(Panel(
            f"[bold]{info['title']}[/bold]\n"
            f"👤 Instructor: [cyan]{info['author_name']}[/cyan] | ⏱️ Duration: [yellow]{info['duration']}[/yellow] | 📝 Words: [green]{info['total_words']:,}[/green]",
            title="[bold green]Video Loaded[/bold green]",
            border_style="green"
        ))

        if args.mode == "curriculum":
            console.print("\n[bold cyan]Generating Tutorial Roadmap...[/bold cyan]\n")
            res = agent.generate_curriculum()
            console.print(Markdown(res))

        elif args.mode == "code":
            console.print("\n[bold cyan]Extracting Code and Commands...[/bold cyan]\n")
            res = agent.extract_code()
            console.print(Markdown(res))

        elif args.mode == "notes":
            console.print("\n[bold cyan]Generating Study Notes & Cheatsheet...[/bold cyan]\n")
            res = agent.generate_study_notes()
            console.print(Markdown(res))

        elif args.mode == "quiz":
            console.print("\n[bold cyan]Generating Mastery Quiz...[/bold cyan]\n")
            res = agent.generate_quiz()
            console.print(Markdown(res))

        elif args.mode == "factcheck":
            console.print("\n[bold cyan]🔍 Auditing Technical Claims with DuckDuckGo Search & Groq AI...[/bold cyan]\n")
            fc_data = agent.fact_check()
            if not fc_data.get("needs_verification"):
                console.print(f"[yellow]Verification Skipped:[/yellow] {fc_data.get('skip_reason')}")
            elif fc_data.get("status") == "error":
                console.print(f"[bold red]Fact Check Error:[/bold red] {fc_data.get('error')}")
            else:
                claims = fc_data.get("claims", [])
                console.print(f"[bold green]Audited {len(claims)} Technical Claims:[/bold green]\n")
                for i, c in enumerate(claims, 1):
                    status = c.get("status", "unverified")
                    if status == "still_valid":
                        badge = "[bold green]✅ STILL VALID[/bold green]"
                        border = "green"
                    elif status == "outdated":
                        badge = "[bold yellow]⚠️ OUTDATED - BREAKING CHANGE[/bold yellow]"
                        border = "yellow"
                    else:
                        badge = "[bold white]❓ UNVERIFIED[/bold white]"
                        border = "dim"

                    ts = f" at {c.get('timestamp')}" if c.get("timestamp") else ""
                    content = (
                        f"{badge}\n\n"
                        f"[bold]Claim:{ts}[/bold] \"{c.get('claim')}\"\n\n"
                        f"[cyan]Audit:[/cyan] {c.get('explanation')}\n"
                    )
                    if status == "outdated" and c.get("corrected_info"):
                        content += f"\n[bold red]⚡ Modern Replacement:[/bold red] [yellow]{c.get('corrected_info')}[/yellow]\n"
                    if c.get("sources"):
                        content += f"\n[dim]Sources: {' | '.join(c.get('sources')[:2])}[/dim]"

                    console.print(Panel(content, title=f"Claim #{i}", border_style=border))

        elif args.mode == "pdf":
            console.print("\n[bold cyan]Generating Tutorial Report PDF with Fact Check...[/bold cyan]")
            pdf_bytes = agent.export_pdf()
            filename = f"tutorial_report_{info.get('video_id', 'export')}.pdf"
            with open(filename, "wb") as f:
                f.write(pdf_bytes)
            console.print(f"[bold green]✅ PDF successfully saved to:[/bold green] {filename}")

        elif args.mode == "chat":
            interactive_chat(agent)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
