"""
Semantic Search CLI Commands

Provides commands for indexing test artifacts and performing semantic similarity searches.
"""

import click
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.config.loader import ConfigLoader
from core.ai.embeddings.semantic_service import SemanticSearchService
from core.logging.logger import get_logger, LogCategory
from cli.progress import Progress
from cli.errors import CommandError

console = Console()
logger = get_logger(__name__, LogCategory.CLI)


@click.group(name='semantic')
def semantic_group():
    """Semantic search and similarity commands"""
    pass


@semantic_group.command(name='index')
@click.option('--framework', '-f', type=click.Choice(['pytest', 'robot', 'cypress', 'playwright', 'java']),
              help='Framework to index tests from')
@click.option('--path', '-p', type=click.Path(exists=True), required=True,
              help='Path to test files or directory')
@click.option('--entity-type', '-t', type=click.Choice(['test', 'scenario', 'failure']),
              default='test', help='Type of entities to index')
@click.option('--batch-size', '-b', type=int, default=100,
              help='Batch size for indexing')
@click.option('--reindex', is_flag=True,
              help='Reindex existing entities with new embeddings')
def index_command(framework: Optional[str], path: str, entity_type: str, batch_size: int, reindex: bool):
    """
    Index test artifacts for semantic search.
    
    Examples:
        crossbridge semantic index -f pytest -p ./tests
        crossbridge semantic index -f robot -p ./tests --entity-type scenario
        crossbridge semantic index -f cypress -p ./cypress/e2e --reindex
    """
    try:
        # Load config
        config_loader = ConfigLoader()
        config = config_loader.load()
        
        # Check if semantic search is enabled
        semantic_config = config.semantic_search.get_effective_config(config.mode)
        if semantic_config.enabled == False:
            raise CommandError("Semantic search is disabled in configuration")
        
        # Initialize service
        service = SemanticSearchService(config_loader=config_loader)
        
        # Display indexing plan
        console.print(Panel(
            f"[bold]Semantic Indexing Plan[/bold]\n\n"
            f"Framework: {framework or 'Auto-detect'}\n"
            f"Path: {path}\n"
            f"Entity Type: {entity_type}\n"
            f"Batch Size: {batch_size}\n"
            f"Reindex: {'Yes' if reindex else 'No'}\n"
            f"Provider: {semantic_config.provider_type} ({service.provider.model_name})",
            title="📊 Indexing Configuration"
        ))
        
        # Discover test files
        test_path = Path(path)
        test_files = []
        
        if test_path.is_file():
            test_files = [test_path]
        else:
            # Discover based on framework
            patterns = {
                'pytest': ['test_*.py', '*_test.py'],
                'robot': ['*.robot'],
                'cypress': ['*.cy.js', '*.cy.ts'],
                'playwright': ['*.spec.js', '*.spec.ts'],
                'java': ['*Test.java']
            }
            
            if framework:
                for pattern in patterns.get(framework, ['*']):
                    test_files.extend(test_path.rglob(pattern))
            else:
                # Auto-detect all test files
                for patterns_list in patterns.values():
                    for pattern in patterns_list:
                        test_files.extend(test_path.rglob(pattern))
        
        if not test_files:
            console.print(f"[yellow]⚠ No test files found in {path}[/yellow]")
            return
        
        console.print(f"\n[cyan]Found {len(test_files)} test files[/cyan]\n")
        
        # Parse and index (simplified - real implementation would parse each framework)
        indexed_count = 0
        error_count = 0
        
        with Progress() as progress:
            task = progress.add_task(f"[cyan]Indexing {entity_type}s...", total=len(test_files))
            
            for test_file in test_files:
                try:
                    # Simplified: Create basic entity from file
                    # Real implementation would parse framework-specific syntax
                    entity_id = f"{entity_type}_{test_file.stem}"
                    
                    service.index_entity(
                        entity_id=entity_id,
                        entity_type=entity_type,
                        test_name=test_file.stem,
                        description=f"Test from {test_file.name}",
                        framework=framework or "unknown",
                        file_path=str(test_file)
                    )
                    
                    indexed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to index {test_file}: {e}")
                    error_count += 1
                
                progress.update(task, advance=1)
        
        # Display results
        console.print(f"\n[green]✓ Successfully indexed {indexed_count} {entity_type}s[/green]")
        if error_count > 0:
            console.print(f"[yellow]⚠ Failed to index {error_count} {entity_type}s[/yellow]")
        
        # Display statistics
        stats = service.get_statistics()
        console.print(f"\n[cyan]Total entities in vector store: {stats['total_entities']}[/cyan]")
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        raise CommandError(f"Indexing failed: {e}")


@semantic_group.command(name='search')
@click.argument('query', type=str)
@click.option('--top-k', '-k', type=int, default=10,
              help='Number of results to return')
@click.option('--entity-type', '-t', type=click.Choice(['test', 'scenario', 'failure', 'all']),
              default='all', help='Filter by entity type')
@click.option('--min-score', '-s', type=float,
              help='Minimum similarity score (0-1)')
@click.option('--json', 'output_json', is_flag=True,
              help='Output results as JSON')
def search_command(query: str, top_k: int, entity_type: str, min_score: Optional[float], output_json: bool):
    """
    Search for similar test artifacts using natural language.
    
    Examples:
        crossbridge semantic search "login timeout error"
        crossbridge semantic search "authentication tests" --top-k 5
        crossbridge semantic search "API validation" --entity-type test --min-score 0.8
    """
    try:
        # Load config
        config_loader = ConfigLoader()
        config = config_loader.load()
        
        # Check if semantic search is enabled
        semantic_config = config.semantic_search.get_effective_config(config.mode)
        if semantic_config.enabled == False:
            raise CommandError("Semantic search is disabled in configuration")
        
        # Initialize service
        service = SemanticSearchService(config_loader=config_loader)
        
        # Perform search
        entity_filter = None if entity_type == 'all' else entity_type
        results = service.search(
            query=query,
            top_k=top_k,
            entity_type=entity_filter,
            min_score=min_score
        )
        
        if not results:
            console.print(f"\n[yellow]No results found for query: {query}[/yellow]")
            return
        
        # Display results
        if output_json:
            import json
            output = {
                'query': query,
                'results': [
                    {
                        'id': r.id,
                        'type': r.entity_type,
                        'score': r.score,
                        'text': r.text,
                        'metadata': r.metadata
                    }
                    for r in results
                ]
            }
            console.print(json.dumps(output, indent=2))
        else:
            # Rich table output
            table = Table(title=f"🔍 Search Results for: {query}")
            table.add_column("Score", style="cyan", width=8)
            table.add_column("Type", style="magenta", width=10)
            table.add_column("ID", style="green")
            table.add_column("Preview", style="white", width=50)
            
            for result in results:
                # Truncate text preview
                preview = result.text[:150] + "..." if len(result.text) > 150 else result.text
                table.add_row(
                    f"{result.score:.3f}",
                    result.entity_type,
                    result.id,
                    preview
                )
            
            console.print()
            console.print(table)
            console.print(f"\n[cyan]Found {len(results)} similar entities[/cyan]")
    
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise CommandError(f"Search failed: {e}")


@semantic_group.command(name='similar')
@click.argument('entity_id', type=str)
@click.option('--top-k', '-k', type=int, default=10,
              help='Number of similar entities to return')
@click.option('--json', 'output_json', is_flag=True,
              help='Output results as JSON')
def similar_command(entity_id: str, top_k: int, output_json: bool):
    """
    Find entities similar to a given entity.
    
    Examples:
        crossbridge semantic similar test_login_timeout
        crossbridge semantic similar scenario_user_authentication --top-k 5
    """
    try:
        # Load config
        config_loader = ConfigLoader()
        config = config_loader.load()
        
        # Check if semantic search is enabled
        semantic_config = config.semantic_search.get_effective_config(config.mode)
        if semantic_config.enabled == False:
            raise CommandError("Semantic search is disabled in configuration")
        
        # Initialize service
        service = SemanticSearchService(config_loader=config_loader)
        
        # Find similar entities
        results = service.find_similar(entity_id=entity_id, top_k=top_k)
        
        if not results:
            console.print(f"\n[yellow]No similar entities found for: {entity_id}[/yellow]")
            return
        
        # Display results
        if output_json:
            import json
            output = {
                'entity_id': entity_id,
                'similar': [
                    {
                        'id': r.id,
                        'type': r.entity_type,
                        'score': r.score,
                        'text': r.text,
                        'metadata': r.metadata
                    }
                    for r in results
                ]
            }
            console.print(json.dumps(output, indent=2))
        else:
            # Rich table output
            table = Table(title=f"🔗 Entities Similar to: {entity_id}")
            table.add_column("Score", style="cyan", width=8)
            table.add_column("Type", style="magenta", width=10)
            table.add_column("ID", style="green")
            table.add_column("Preview", style="white", width=50)
            
            for result in results:
                # Truncate text preview
                preview = result.text[:150] + "..." if len(result.text) > 150 else result.text
                table.add_row(
                    f"{result.score:.3f}",
                    result.entity_type,
                    result.id,
                    preview
                )
            
            console.print()
            console.print(table)
            console.print(f"\n[cyan]Found {len(results)} similar entities[/cyan]")
    
    except Exception as e:
        logger.error(f"Finding similar entities failed: {e}", exc_info=True)
        raise CommandError(f"Finding similar entities failed: {e}")


@semantic_group.command(name='stats')
@click.option('--json', 'output_json', is_flag=True,
              help='Output statistics as JSON')
def stats_command(output_json: bool):
    """
    Display semantic search system statistics.
    
    Examples:
        crossbridge semantic stats
        crossbridge semantic stats --json
    """
    try:
        # Load config
        config_loader = ConfigLoader()
        config = config_loader.load()
        
        # Check if semantic search is enabled
        semantic_config = config.semantic_search.get_effective_config(config.mode)
        if semantic_config.enabled == False:
            raise CommandError("Semantic search is disabled in configuration")
        
        # Initialize service
        service = SemanticSearchService(config_loader=config_loader)
        
        # Get statistics
        stats = service.get_statistics()
        
        if output_json:
            import json
            console.print(json.dumps(stats, indent=2))
        else:
            # Rich panel output
            stats_text = f"""
[bold]Total Entities:[/bold] {stats['total_entities']}
[bold]Entity Types:[/bold] {', '.join(f"{k}: {v}" for k, v in stats['entity_counts'].items())}
[bold]Embedding Versions:[/bold] {', '.join(stats['versions'])}
[bold]Provider:[/bold] {stats['provider_type']} ({stats['provider_model']})
[bold]Dimensions:[/bold] {stats['embedding_dimensions']}
            """
            
            console.print(Panel(stats_text.strip(), title="📊 Semantic Search Statistics"))
    
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}", exc_info=True)
        raise CommandError(f"Failed to get statistics: {e}")
