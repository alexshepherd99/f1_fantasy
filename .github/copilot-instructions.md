# Copilot Instructions for f1_fantasy Repository

## Overview
This file contains guidelines for GitHub Copilot when assisting with development in the f1_fantasy repository. These instructions help ensure consistency, quality, and adherence to project standards.

## Agent behaviour
- Start any development process by running the tests in the associated area, to ensure they run clean.
- Use test-driven development for new code, and a red/green testing approach.
- Ensure the full suite of pytest repo unit tests work before marking any work as complete.
- Present options and ask for clarification often.
- Propose updates to this instructions file for any best practice changes identified during development.
- For larger changes impacting more than three functions, propose a plan which can be saved then implemented within a fresh chat context.
- Plans and specifications will be saved down to the agent_docs folder in this repo.
- *** SAVE DOCS LOCATION ***
- When creating unit tests, avoid mocking existing functions if possible.
- When importing modules, always use fully qualified module paths, never relative paths.
- Prefer simple code.
- Use established design patterns where relevant and appropriate.
- Read full code files right to the end when reviewing the existing code base.

## General Coding Guidelines
- Follow PEP 8 style guidelines for Python code.
- Use meaningful variable and function names.
- Include docstrings for all public functions, classes, and modules.
- Prefer type hints for function parameters and return values.
- Write clear, concise comments where code logic is not self-explanatory.
- Ensure all import statements are fully qualified, and that there are no relative path import statements.

## Project-Specific Rules
- **Data Handling**: When working with F1 data, ensure compatibility with the existing formats in `data/f1_fantasy_archive.xlsx`. Validate data integrity and handle missing values appropriately.
- **Linear Programming**: Use the PuLP library for optimization problems. Structure constraints and objectives clearly.
- **Testing**: Write unit tests for new functionality using pytest. Place tests in the `tests/` directory following the existing naming conventions.
- **Dependencies**: Avoid adding new dependencies unless necessary. If adding, update `requirements.txt` and justify the addition.
- **Performance**: Consider execution time for back-testing scripts; optimize where possible without sacrificing readability.

## Code Structure
- Keep functions small and focused on a single responsibility.
- Use classes for organizing related data and methods (e.g., in `races/` and `linear/` modules).
- Follow the existing module structure: separate concerns into appropriate directories like `scripts/`, `external_data/`, etc.

## Error Handling
- Implement proper exception handling for file I/O, data parsing, and external API calls.
- Log errors and warnings using Python's logging module where appropriate.

## Best Practices
- Commit changes with descriptive messages.
- Ensure code passes all existing tests before suggesting changes.
- When modifying existing code, preserve backward compatibility unless explicitly required otherwise.

## Additional Notes
- This project focuses on F1 Fantasy optimization using linear programming.
- Prioritize code maintainability and readability over premature optimization.
- If unsure about a guideline, refer to the README.md or existing codebase for examples.