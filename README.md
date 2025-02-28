# AI PR Insight

AI PR Insight is a powerful command-line tool that extracts and analyzes pull request (PR) comments from GitHub repositories. Using OpenAI's GPT models, it generates actionable checklists and insights to help developers improve their code review process.

## Features

- **Fetch PR Comments**: Extract PR comments from GitHub repositories you have access to.
- **AI-Powered Analysis**: Use OpenAI's GPT models to analyze comments and generate actionable insights.
- **Checklist Generation**: Create a checklist of best practices and common issues from PR comments.
- **Customizable Filters**: Filter comments by year, month, organization, or repository.
- **Standalone CLI**: Easy-to-use command-line interface for seamless integration into your workflow.
- **Summarization**: Consolidate and summarize PR analysis results for better insights.
- **Verbose Logging**: Debug mode available for detailed logs during execution.

---

## Installation

### Prerequisites

Ensure you have the following before installation:

- Python 3.8 or higher
- A GitHub personal access token (with `repo` scope)
- An OpenAI API key

### Install via pip

```bash
pip3 install ai-pr-insight
```

### Manual Installation

```bash
git clone https://github.com/kadivar/ai-pr-insight.git
cd ai-pr-insight
pip3 install -r requirements.txt
```

---

## Usage

AI PR Insight provides three main commands: `fetch`, `analyze`, and `summarize`.

### Fetch PR Comments

To fetch PR comments from a specific year and month within an organization:

```bash
ai-pr-insight fetch --year 2024 --month 2 --org my-org --output_file pr-comments.json
```

You can also filter by a specific GitHub username:

```bash
ai-pr-insight fetch --year 2024 --month 2 --username my-user --output_file pr-comments.json
```

### Analyze PR Comments

To analyze PR comments and generate a checklist:

```bash
ai-pr-insight analyze --input_file pr-comments.json --output_dir output --batch-size 20 --model-tier premium
```

- `batch-size`: Number of comments to process in each batch.
- `model-tier`: Choose between `economy` (GPT-3.5) and `premium` (GPT-4).

### Summarize PR Analysis Results

To consolidate and summarize analysis results:

```bash
ai-pr-insight summarize --input_dir analysis_results --output_dir summary_results --similarity-threshold 0.9 --abstraction-threshold 0.85
```

- `similarity-threshold`: Defines similarity grouping (range: 0.0 - 1.0).
- `abstraction-threshold`: Defines abstraction grouping (range: 0.0 - 1.0).

### Enable Debug Mode

For detailed logs, add the `--verbose` flag:

```bash
ai-pr-insight fetch --year 2024 --month 2 --org my-org --output_file pr-comments.json --verbose
```

---

## Configuration

AI PR Insight uses a `.env` file for configuration. Place this file in the root directory with the following variables:

```ini
GITHUB_TOKEN=your_github_personal_access_token
OPENAI_API_KEY=your_openai_api_key
CACHE_EXPIRATION_MINUTES=120
DEBUG=false
SOURCE_CODE_LINES_OFFSET=3
```

### Environment Variables Explained

- `GITHUB_TOKEN`: Your GitHub personal access token (required).
- `OPENAI_API_KEY`: Your OpenAI API key (required).
- `CACHE_EXPIRATION_MINUTES`: Cache expiration time in minutes (default: 120).
- `DEBUG`: Enable debug mode (default: false).
- `SOURCE_CODE_LINES_OFFSET`: Number of lines to include around a code snippet (default: 3).

---

## Running Tests

Run them using:

```bash
python3 -m unittest discover tests
```

---

## Example Outputs

### Example PR Comments Output (`pr-comments.json`)

```json
[
    {
        "author": "johndoe",
        "repository": "surveyanyplace/survey-ui",
        "pr_number": 1234,
        "pr_title": "Refactor UserProfile component to use hooks [SA-12345]",
        "pr_url": "https://github.com/surveyanyplace/survey-ui/pull/1234",
        "datetime": "2025-03-15T14:45:22Z",
        "message": "A: I think we should also consider adding error handling for the API call in this component.",
        "comment_url": "https://github.com/surveyanyplace/survey-ui/pull/1234#discussion_r1987654321",
        "permalink": "https://github.com/surveyanyplace/survey-ui/pull/1234#discussion_r1987654321",
        "source_code": "import React, { useEffect, useState } from 'react';\nimport axios from 'axios';\n\nconst UserProfile = ({ userId }) => {\n  const [user, setUser] = useState(null);\n  const [loading, setLoading] = useState(true);\n  const [error, setError] = useState(null);\n\n  useEffect(() => {\n    const fetchUserProfile = async () => {\n      try {\n        const response = await axios.get(`/api/users/${userId}`);\n        setUser(response.data);\n      } catch (err) {\n        setError(err);\n      } finally {\n        setLoading(false);\n      }\n    };\n\n    fetchUserProfile();\n  }, [userId]);\n\n  if (loading) return <div>Loading...</div>;\n  if (error) return <div>Error: {error.message}</div>;\n\n  return (\n    <div>\n      <h1>{user.name}</h1>\n      <p>{user.email}</p>\n    </div>\n  );\n};\n\nexport default UserProfile;"
    }
]
```

### Example Checklist Output (`checklist.md`)

```markdown
# PR Review Checklist

- [ ] Refactor complex functions for better readability.
- [ ] Improve documentation for unclear code sections.
- [ ] Ensure tests cover newly introduced changes.
```

---

## License

AI PR Insight is licensed under the GNU Affero General Public License (AGPL). See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to get started.

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.

**Made with ❤️ by Mohammadreza Kadivar**
