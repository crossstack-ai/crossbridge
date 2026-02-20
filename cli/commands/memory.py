"""
CLI commands for Memory and Semantic Search features in CrossBridge.

Commands:
- memory ingest: Ingest test data into memory system
- memory stats: Show memory statistics
- search query: Semantic search for tests
- search similar: Find similar tests
"""

import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


from core.memory import (
    MemoryIngestionPipeline,
    SemanticSearchEngine,
    create_embedding_provider,
    create_vector_store,
)
from core.memory.models import MemoryType
from core.config.loader import get_config
from core.logging import get_logger, LogCategory

def _check_ai_semantic_enabled():
    config = get_config()
    logger = get_logger("cli.memory", category=LogCategory.CLI)
    ai_enabled = getattr(config.ai, "enabled", False)
    semantic_enabled = getattr(config.semantic_search, "enabled", False)
    # Support 'auto' (enable in migration mode)
    if isinstance(semantic_enabled, str) and semantic_enabled == "auto":
        semantic_enabled = config.mode == "migration"
    if not ai_enabled or not semantic_enabled:
        msg = (
            "[yellow]AI and/or semantic search features are disabled in your configuration. "
            "To enable semantic search, set [bold]ai.enabled: true[/bold] and [bold]semantic_search.enabled: true[/bold] in crossbridge.yml.[/yellow]"
        )
        logger.warning("Semantic/AI features are disabled. Skipping command.")
        console.print(msg)
        raise typer.Exit(0)

console = Console()

memory_app = typer.Typer(help="Memory and embeddings management")
search_app = typer.Typer(help="Semantic search for tests")


def get_pipeline():
    """Get configured memory ingestion pipeline from config."""
    try:
        import yaml


        config_path = Path("crossbridge.yml")
        if not config_path.exists():
            console.print(
                "[red]Error: crossbridge.yml not found. Please configure memory system.[/red]"
            )
            raise typer.Exit(1)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # New: Read embedding/vector config from crossbridge -> ai -> semantic_engine
        cb_config = config.get("crossbridge", {})
        ai_config = cb_config.get("ai", {})
        sem_config = ai_config.get("semantic_engine", {})
        embedding_config = sem_config.get("embedding", {})
        vector_store_config = sem_config.get("vector_store", {})

        # Embedding provider selection
        provider_type = embedding_config.get("provider", "openai")
        provider_args = {}
        # Map config keys to provider args
        if "model" in embedding_config:
            provider_args["model"] = embedding_config["model"]
        if "api_key" in embedding_config:
            provider_args["api_key"] = embedding_config["api_key"]
        if "batch_size" in embedding_config:
            provider_args["batch_size"] = embedding_config["batch_size"]
        if provider_type == "local":
            # For local/ollama, support base_url
            ollama_cfg = ai_config.get("ollama", {})
            if "base_url" in ollama_cfg:
                provider_args["base_url"] = ollama_cfg["base_url"]
            if "model" in ollama_cfg:
                provider_args["model"] = ollama_cfg["model"]

        provider = create_embedding_provider(provider_type, **provider_args)

        # Vector store selection
        store_type = vector_store_config.get("type", "pgvector")
        store_args = {}
        if "storage_path" in vector_store_config:
            store_args["storage_path"] = vector_store_config["storage_path"]
        if "index_type" in vector_store_config:
            store_args["index_type"] = vector_store_config["index_type"]
        if "distance_metric" in vector_store_config:
            store_args["distance_metric"] = vector_store_config["distance_metric"]
        if "probes" in vector_store_config:
            store_args["probes"] = vector_store_config["probes"]
        if "maintenance_interval" in vector_store_config:
            store_args["maintenance_interval"] = vector_store_config["maintenance_interval"]

        store = create_vector_store(store_type, **store_args)

        # Batch size
        batch_size = embedding_config.get("batch_size", 100)
        pipeline = MemoryIngestionPipeline(provider, store, batch_size=batch_size)

        return pipeline, provider, store

    except Exception as e:
        console.print(f"[red]Failed to initialize memory system: {e}[/red]")
        raise typer.Exit(1)


@memory_app.command("ingest")
def memory_ingest(
    source: str = typer.Option(
        ...,
        "--source",
        "-s",
        help="Source directory or file to ingest",
    ),
    framework: Optional[str] = typer.Option(
        None,
        "--framework",
        "-f",
        help="Framework filter (pytest, cypress, etc.)",
    ),
    entity_types: Optional[List[str]] = typer.Option(
        None,
        "--type",
        "-t",
        help="Entity types to ingest (test, scenario, step, etc.)",
    ),
):
    """
    Ingest test data into memory system.
    
    Examples:
        crossbridge memory ingest --source ./tests --framework pytest
        crossbridge memory ingest --source discovery_results.json --type test scenario
    """
    console.print("[bold blue]🔄 Starting memory ingestion...[/bold blue]")

    pipeline, _, _ = get_pipeline()

    # Check if source is JSON file or directory
    source_path = Path(source)

    if source_path.is_file() and source_path.suffix == ".json":
        # Load from JSON file (discovery results)
        with open(source_path) as f:
            data = json.load(f)

        from core.memory.ingestion import ingest_from_discovery

        counts = ingest_from_discovery(data, pipeline)

        table = Table(title="Ingestion Results", box=box.ROUNDED)
        table.add_column("Entity Type", style="cyan")
        table.add_column("Count", style="green")

        for entity_type, count in counts.items():
            table.add_row(entity_type, str(count))

        console.print(table)
        console.print(
            f"[bold green]✅ Successfully ingested {sum(counts.values())} records[/bold green]"
        )

    else:
        console.print(
            "[yellow]⚠️  Directory ingestion not yet implemented. Use JSON discovery results.[/yellow]"
        )
        console.print(
            "[dim]Run 'crossbridge discover' first and save results to JSON.[/dim]"
        )


@memory_app.command("stats")
def memory_stats():
    """
    Show memory system statistics.
    
    Example:
        crossbridge memory stats
    """
    console.print("[bold blue]📊 Memory System Statistics[/bold blue]\n")

    pipeline, _, _ = get_pipeline()
    stats = pipeline.get_stats()

    table = Table(title="Memory Records by Type", box=box.ROUNDED)
    table.add_column("Entity Type", style="cyan")
    table.add_column("Count", style="green", justify="right")

    # Total
    table.add_row("[bold]Total Records[/bold]", f"[bold]{stats['total']}[/bold]")

    # By type
    for memory_type in MemoryType:
        count_key = f"{memory_type.value}_count"
        if count_key in stats:
            table.add_row(memory_type.value.capitalize(), str(stats[count_key]))

    console.print(table)


@memory_app.command("clear")
def memory_clear(
    entity_types: Optional[List[str]] = typer.Option(
        None,
        "--type",
        "-t",
        help="Entity types to clear (or all if not specified)",
    ),
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """
    Clear memory records.
    
    Example:
        crossbridge memory clear --type failure
        crossbridge memory clear --yes  # Clear all
    """
    if not confirm:
        if entity_types:
            msg = f"Clear all {', '.join(entity_types)} records?"
        else:
            msg = "Clear ALL memory records?"

        if not typer.confirm(msg):
            console.print("[yellow]❌ Cancelled[/yellow]")
            raise typer.Exit(0)

    console.print("[yellow]⚠️  Memory clearing not yet fully implemented[/yellow]")


@search_app.command("query")
def search_query(
    query: str = typer.Argument(..., help="Natural language search query"),
    entity_types: Optional[List[str]] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by entity types (test, scenario, step, etc.)",
    ),
    framework: Optional[str] = typer.Option(
        None,
        "--framework",
        "-f",
        help="Filter by framework",
    ),
    top_k: int = typer.Option(
        10,
        "--top",
        "-k",
        help="Maximum number of results",
    ),
    explain: bool = typer.Option(
        False,
        "--explain",
        "-e",
        help="Show explanation for matches",
    ),
):
    """
    Semantic search for tests and scenarios.
    
    Examples:
        crossbridge search query "tests covering login timeout"
        crossbridge search query "payment edge cases" --type scenario
        crossbridge search query "flaky auth tests" --framework pytest --top 5
    """
    console.print(f'[bold blue]🔍 Searching for: "{query}"[/bold blue]\n')


    _check_ai_semantic_enabled()
    _, provider, store = get_pipeline()
    engine = SemanticSearchEngine(provider, store)

    results = engine.search(
        query=query,
        entity_types=entity_types,
        framework=framework,
        top_k=top_k,
    )

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    # Display results
    table = Table(
        title=f"Search Results ({len(results)} found)",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", style="cyan", width=10)
    table.add_column("ID", style="yellow")
    table.add_column("Score", style="green", width=8)
    table.add_column("Preview", style="white")

    for result in results:
        # Truncate text preview
        preview = result.record.text.replace("\n", " ")[:80]
        if len(result.record.text) > 80:
            preview += "..."

        table.add_row(
            str(result.rank),
            result.record.type.value,
            result.record.id,
            f"{result.score:.3f}",
            preview,
        )

    console.print(table)

    # Show detailed info for top result
    if results:
        top_result = results[0]
        console.print("\n[bold]📋 Top Result Details:[/bold]")

        # Create panel with result details
        details = [
            f"[cyan]ID:[/cyan] {top_result.record.id}",
            f"[cyan]Type:[/cyan] {top_result.record.type.value}",
            f"[cyan]Score:[/cyan] {top_result.score:.3f}",
        ]


        if metadata := top_result.record.metadata:
            details.append("[cyan]Metadata:[/cyan]")
            for key, value in metadata.items():
                if value:
                    details.append(f"  • {key}: {value}")

        details.append(f"\n[cyan]Text:[/cyan]\n{top_result.record.text}")

        if explain:
            explanation = engine.explain_search(query, top_result)
            details.append(f"\n[cyan]Explanation:[/cyan]\n{explanation}")

        panel = Panel(
            "\n".join(details),
            title="Top Match",
            border_style="green",
        )
        console.print(panel)


@search_app.command("similar")
def search_similar(
    record_id: str = typer.Argument(..., help="Record ID to find similar records for"),
    entity_types: Optional[List[str]] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by entity types",
    ),
    top_k: int = typer.Option(
        5,
        "--top",
        "-k",
        help="Maximum number of results",
    ),
):
    """
    Find tests/scenarios similar to a given one.
    
    Examples:
        crossbridge search similar test_login_valid
        crossbridge search similar test_checkout --type test --top 10
    """
    console.print(f'[bold blue]🔍 Finding records similar to: "{record_id}"[/bold blue]\n')


    _check_ai_semantic_enabled()
    _, provider, store = get_pipeline()
    engine = SemanticSearchEngine(provider, store)

    results = engine.find_similar(
        record_id=record_id,
        entity_types=entity_types,
        top_k=top_k,
    )

    if not results:
        console.print("[yellow]No similar records found[/yellow]")
        return

    # Display results
    table = Table(
        title=f"Similar Records ({len(results)} found)",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", style="cyan", width=10)
    table.add_column("ID", style="yellow")
    table.add_column("Similarity", style="green", width=10)
    table.add_column("Preview", style="white")

    for result in results:
        preview = result.record.text.replace("\n", " ")[:60]
        if len(result.record.text) > 60:
            preview += "..."

        # Color code similarity
        if result.score > 0.9:
            similarity_color = "red"  # Potential duplicate
        elif result.score > 0.7:
            similarity_color = "yellow"  # Very similar
        else:
            similarity_color = "green"  # Somewhat similar

        table.add_row(
            str(result.rank),
            result.record.type.value,
            result.record.id,
            f"[{similarity_color}]{result.score:.3f}[/{similarity_color}]",
            preview,
        )

    console.print(table)

    # Show duplicate warning if very high similarity
    high_similarity = [r for r in results if r.score > 0.9]
    if high_similarity:
        console.print(
            f"\n[yellow]⚠️  Found {len(high_similarity)} potential duplicate(s) (similarity > 0.9)[/yellow]"
        )


@search_app.command("duplicates")
def search_duplicates(
    framework: Optional[str] = typer.Option(
        None,
        "--framework",
        "-f",
        help="Filter by framework (pytest, robot, selenium-java, etc.)",
    ),
    threshold: float = typer.Option(
        0.9,
        "--threshold",
        "-t",
        help="Similarity threshold for duplicates (default: 0.9)",
    ),
    test_dir: str = typer.Option(
        ".",
        "--test-dir",
        help="Root directory to search for tests (default: current directory). Use to specify a custom test folder.",
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output-file",
        help="Path to Robot output.xml file (default: output.xml in current directory). Use to specify a custom location.",
    ),
):
    """
    Find potential duplicate tests using semantic similarity.

    Example:
        crossbridge search duplicates --framework robot --test-dir /path/to/robot/tests --output-file /path/to/output.xml
        crossbridge search duplicates --framework pytest --threshold 0.95 --test-dir path/to/tests

    Notes:
        - Use --test-dir to specify the root directory for test discovery (default: current directory).
        - For Robot Framework: .robot files should be in the specified directory. Use --output-file to specify the location of output.xml if it is not in the current directory.
        - For pytest: Test files should be in the specified directory or match 'test_*.py' or '*_test.py' patterns.
        - For Java/Selenium: Test sources should be in 'src/test/java' under the specified directory or the standard Maven/Gradle test directory structure.
        - For other frameworks: Ensure your test files or result files are in their standard locations, or update your configuration accordingly.
        - If no tests are found, check your test directory structure, file locations, and that any required result files (like output.xml) are present.
    """

    _check_ai_semantic_enabled()
    from core.ai.semantic.duplicate_detection import DuplicateDetector
    from core.ai.semantic.semantic_search_service import SemanticSearchService
    from core.memory import create_embedding_provider, create_vector_store
    from core.memory.models import convert_test_to_text, MemoryType
    from cli.main import AdapterRegistry
    from adapters.common.models import TestMetadata
    import traceback

    console.print("[bold blue]🔍 Searching for duplicate tests...[/bold blue]\n")
    logger = None
    try:
        from core.logging import get_logger, LogCategory
        logger = get_logger("search_duplicates", category=LogCategory.AI)
    except Exception:
        pass

    # Step 1: Discover frameworks
    project_root = test_dir or "."
    frameworks = [framework] if framework else AdapterRegistry.auto_detect_frameworks(project_root)
    robot_output_path = output_file if output_file else "output.xml"
    if not frameworks:
        console.print("[red]No supported test frameworks found in project.[/red]")
        raise typer.Exit(1)

    all_tests = []
    for fw in frameworks:
        try:
            if AdapterRegistry.is_extractor(fw):
                if fw == "robot":
                    extractor = AdapterRegistry.get_extractor(fw, project_root, output_path=robot_output_path)
                else:
                    extractor = AdapterRegistry.get_extractor(fw, project_root)
                tests = extractor.extract_tests()
            else:
                adapter = AdapterRegistry.get_adapter(fw, project_root)
                # Try to get rich metadata if possible
                if hasattr(adapter, "extract_tests"):
                    tests = adapter.extract_tests()
                elif hasattr(adapter, "discover_tests"):
                    # Only test names, wrap as TestMetadata
                    test_names = adapter.discover_tests()
                    tests = [TestMetadata(framework=fw, test_name=name, file_path="", tags=[]) for name in test_names]
                else:
                    tests = []
            all_tests.extend(tests)
        except Exception as e:
            if logger:
                logger.error(f"Failed to discover tests for {fw}: {e}\n{traceback.format_exc()}")
            console.print(f"[yellow]Warning: Could not discover tests for {fw}: {e}[/yellow]")

    if not all_tests:
        console.print("[yellow]No tests found to analyze for duplicates.[/yellow]")
        raise typer.Exit(0)

    # Step 2: Prepare test data for duplicate detection
    test_dicts = []
    for t in all_tests:
        # t may be TestMetadata or dict
        test_dicts.append({
            "id": getattr(t, "id", getattr(t, "test_name", str(t))),
            "name": getattr(t, "name", getattr(t, "test_name", str(t))),
            "framework": getattr(t, "framework", None),
            "tags": getattr(t, "tags", []),
            "file": getattr(t, "file_path", None),
            "text": convert_test_to_text({
                "name": getattr(t, "name", getattr(t, "test_name", str(t))),
                "framework": getattr(t, "framework", None),
                "tags": getattr(t, "tags", []),
                "file": getattr(t, "file_path", None),
            })
        })

    # Step 3: Set up semantic search and duplicate detector
    try:
        # Use memory config for embedding/vector store
        provider = create_embedding_provider()
        store = create_vector_store()
        semantic_search = SemanticSearchService(provider, store)
        detector = DuplicateDetector(semantic_search, similarity_threshold=threshold)
    except Exception as e:
        if logger:
            logger.error(f"Failed to initialize semantic search: {e}\n{traceback.format_exc()}")
        console.print(f"[red]Failed to initialize semantic search: {e}[/red]")
        raise typer.Exit(1)

    # Step 4: Run duplicate detection
    console.print(f"[dim]Analyzing {len(test_dicts)} tests for duplicates (threshold: {threshold})...[/dim]")
    duplicates = detector.find_all_duplicates(test_dicts, entity_type=MemoryType.TEST.value)

    if not duplicates:
        console.print("[green]No duplicates found above the threshold.[/green]")
        return

    # Step 5: Output results
    table = Table(title="Duplicate Tests Detected", box=box.ROUNDED, show_lines=True)
    table.add_column("Test 1", style="cyan")
    table.add_column("Test 2", style="cyan")
    table.add_column("Similarity", style="green")
    table.add_column("Confidence", style="yellow")
    table.add_column("Type", style="magenta")
    table.add_column("Reason(s)", style="white")

    for dup in duplicates:
        table.add_row(
            dup.entity_id_1,
            dup.entity_id_2,
            f"{dup.similarity_score:.3f}",
            f"{dup.confidence:.2f}",
            dup.duplicate_type.value,
            "; ".join(dup.reasons)
        )

    console.print(table)
    console.print(f"[yellow]⚠️  {len(duplicates)} duplicate pairs found (threshold: {threshold})[/yellow]")
    if logger:
        logger.info(f"Duplicate detection complete: {len(duplicates)} pairs found.")


# Register subcommands
app = typer.Typer()
app.add_typer(memory_app, name="memory")
app.add_typer(search_app, name="search")
