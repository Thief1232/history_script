import shutil
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

FIREFOX_ROOT = Path.home() / ".config" / "mozilla" / "firefox"
TOP_SITES_LIMIT = 10
OUTPUT_CHART = Path("history.png")


def find_firefox_history_file() -> Path:
    if not FIREFOX_ROOT.exists():
        raise FileNotFoundError(f"Firefox config directory not found: {FIREFOX_ROOT}")

    candidates = sorted(FIREFOX_ROOT.glob("*.default*/places.sqlite"))
    if not candidates:
        candidates = sorted(FIREFOX_ROOT.glob("*/places.sqlite"))

    if not candidates:
        raise FileNotFoundError("Could not find Firefox history file places.sqlite")

    return candidates[0]


def copy_history_to_temp(src: Path) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="firefox-history-"))
    dst = temp_dir / src.name
    shutil.copy2(src, dst)
    return dst


def fetch_urls(history_db: Path) -> list[str]:
    query = """
        SELECT url
        FROM moz_places
        WHERE hidden = 0 AND url IS NOT NULL
    """
    with sqlite3.connect(history_db) as connection:
        rows = connection.execute(query).fetchall()
    return [row[0] for row in rows]


def extract_domain(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None

    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    return domain or None


def count_domains(urls: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for url in urls:
        domain = extract_domain(url)
        if domain:
            counter[domain] += 1
    return counter


def plot_top_domains(
    domain_counts: Counter[str],
    limit: int = TOP_SITES_LIMIT,
    output_path: Path = OUTPUT_CHART,
) -> Path:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "matplotlib is required for plotting. Install it with: pip install matplotlib"
        ) from error

    most_common = domain_counts.most_common()
    common = most_common[:10:]
    others = most_common[10::]

    if not most_common:
        raise ValueError("No browser history entries were found for plotting")

    labels, visits = [(domain, count) for domain, count in common]
    all_visits = [count for _, count in others]

    # colors
    bar_colors = ['maroon', 'darkblue', 'wheat', 'green', 'gray', 'purple']

    plt.figure(figsize=(12, 6))
    p = plt.bar(labels, visits, color=bar_colors)
    i = plt.bar("others", len(all_visits))
    plt.bar_label(p, padding=3)
    plt.bar_label(i, padding=3)
    plt.title("Most visited Firefox sites")
    plt.xlabel("Domain")
    plt.ylabel("Visits")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path


def main() -> None:
    source_db = find_firefox_history_file()
    temp_db = copy_history_to_temp(source_db)
    urls = fetch_urls(temp_db)
    domain_counts = count_domains(urls)
    chart_path = plot_top_domains(domain_counts)
    print(f"Chart saved to {chart_path.resolve()}")


if __name__ == "__main__":
    main()
