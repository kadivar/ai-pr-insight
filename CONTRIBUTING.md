# Contributing to AI PR Insight

Thank you for your interest in contributing to AI PR Insight! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone. Please:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue on GitHub with the following information:

1. A clear, descriptive title
2. Steps to reproduce the issue
3. Expected behavior
4. Actual behavior
5. Screenshots (if applicable)
6. Environment details (OS, Python version, package version)

### Suggesting Enhancements

We welcome suggestions for enhancements! Please create an issue with:

1. A clear, descriptive title
2. A detailed description of the proposed feature
3. Any relevant examples or mockups
4. The rationale for the enhancement

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature-name`)
3. Make your changes
4. Add or update tests as necessary
5. Update documentation as needed
6. Run tests to ensure they pass
7. Commit your changes with clear, descriptive commit messages
8. Push to your branch (`git push origin feature/your-feature-name`)
9. Open a pull request

#### Pull Request Guidelines

- Follow the existing code style and conventions
- Include tests for new features or bug fixes
- Update documentation for any changed functionality
- Keep PRs focused on a single change to facilitate review
- Reference relevant issues in your PR description

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/kadivar/ai-pr-insight.git
   cd ai-pr-insight
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Set up environment variables by copying the example:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file with your GitHub token and OpenAI API key.

## Testing

Run tests using:

```bash
python -m unittest discover tests
```

Or if you prefer pytest:

```bash
pytest
```

## Code Style

This project follows PEP 8 style guidelines. We use:
- Black for code formatting
- Flake8 for linting
- isort for import sorting

You can run style checks with:

```bash
black .
flake8
isort .
```

## Documentation

Please update documentation when making changes:

- Update README.md for user-facing changes
- Update docstrings for modified functions or classes
- Add comments for complex code sections

## Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests after the first line

## Versioning

We follow [Semantic Versioning](https://semver.org/) (SemVer):
- MAJOR version for incompatible API changes
- MINOR version for added functionality in a backward-compatible manner
- PATCH version for backward-compatible bug fixes

## License

By contributing to AI PR Insight, you agree that your contributions will be licensed under the project's [GNU Affero General Public License (AGPL)](LICENSE).

## Questions?

If you have any questions or need help, please:
- Open an issue on GitHub
- Contact the project maintainer at [your contact info]

Thank you for contributing to AI PR Insight!
