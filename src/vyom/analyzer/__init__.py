"""Vyom Code Analyzer Module.

Provides comprehensive code analysis including:
- Static analysis for code quality
- Complexity analysis for maintainability
- Security analysis for vulnerabilities
- Performance analysis for optimization
"""

from .static_analyzer import StaticAnalyzer, analyze_code
from .complexity_analyzer import ComplexityAnalyzer, analyze_complexity
from .security_analyzer import SecurityAnalyzer, analyze_security
from .performance_analyzer import PerformanceAnalyzer, analyze_performance

from typing import List, Dict, Any
from ..ast_nodes import Stmt


class VyomAnalyzer:
    """Unified analyzer for Vyom code."""
    
    def __init__(self):
        self.static_analyzer = StaticAnalyzer()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.security_analyzer = SecurityAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
    
    def analyze(self, ast: List[Stmt], options: Dict[str, bool] = None) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of Vyom code.
        
        Args:
            ast: Abstract syntax tree to analyze
            options: Analysis options
                - 'static': Enable static analysis (default: True)
                - 'complexity': Enable complexity analysis (default: True)
                - 'security': Enable security analysis (default: True)
                - 'performance': Enable performance analysis (default: True)
        
        Returns:
            Dictionary containing all analysis results
        """
        if options is None:
            options = {
                'static': True,
                'complexity': True,
                'security': True,
                'performance': True
            }
        
        results = {
            'summary': {
                'total_issues': 0,
                'error_count': 0,
                'warning_count': 0,
                'info_count': 0
            },
            'issues': []
        }
        
        # Static Analysis
        if options.get('static', True):
            static_issues = self.static_analyzer.analyze(ast)
            results['static_analysis'] = static_issues
            results['issues'].extend(static_issues)
        
        # Complexity Analysis
        if options.get('complexity', True):
            complexity_results = self.complexity_analyzer.analyze(ast)
            results['complexity_analysis'] = complexity_results
            
            # Add complexity warnings
            if complexity_results['total_complexity'] > 20:
                results['issues'].append({
                    'severity': 'warning',
                    'line': 0,
                    'message': f"High cyclomatic complexity: {complexity_results['total_complexity']}",
                    'type': 'complexity'
                })
        
        # Security Analysis
        if options.get('security', True):
            security_issues = self.security_analyzer.analyze(ast)
            results['security_analysis'] = security_issues
            results['issues'].extend(security_issues)
        
        # Performance Analysis
        if options.get('performance', True):
            performance_issues = self.performance_analyzer.analyze(ast)
            results['performance_analysis'] = performance_issues
            results['issues'].extend(performance_issues)
        
        # Calculate summary
        for issue in results['issues']:
            results['summary']['total_issues'] += 1
            if issue['severity'] == 'error':
                results['summary']['error_count'] += 1
            elif issue['severity'] == 'warning':
                results['summary']['warning_count'] += 1
            elif issue['severity'] == 'info':
                results['summary']['info_count'] += 1
        
        return results
    
    def quick_analyze(self, ast: List[Stmt]) -> Dict[str, Any]:
        """Quick analysis with only essential checks."""
        return self.analyze(ast, {
            'static': True,
            'complexity': False,
            'security': True,
            'performance': False
        })


# Convenience functions for individual analyses
def analyze_static(ast: List[Stmt]) -> List[Dict[str, Any]]:
    """Analyze code quality and style."""
    return analyze_code(ast)


def analyze_complexity(ast: List[Stmt]) -> Dict[str, Any]:
    """Analyze code complexity."""
    return analyze_complexity(ast)


def analyze_security(ast: List[Stmt]) -> List[Dict[str, Any]]:
    """Analyze security vulnerabilities."""
    return analyze_security(ast)


def analyze_performance(ast: List[Stmt]) -> List[Dict[str, Any]]:
    """Analyze performance issues."""
    return analyze_performance(ast)


def analyze_comprehensive(ast: List[Stmt], options: Dict[str, bool] = None) -> Dict[str, Any]:
    """Perform comprehensive analysis."""
    analyzer = VyomAnalyzer()
    return analyzer.analyze(ast, options)


# Export main classes and functions
__all__ = [
    'VyomAnalyzer',
    'StaticAnalyzer',
    'ComplexityAnalyzer', 
    'SecurityAnalyzer',
    'PerformanceAnalyzer',
    'analyze_static',
    'analyze_complexity',
    'analyze_security',
    'analyze_performance',
    'analyze_comprehensive'
]
