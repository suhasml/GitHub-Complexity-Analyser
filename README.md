# Code Complexity Analyzer

The Code Complexity Analyzer is a tool that analyzes code complexity in repositories on GitHub. It uses OpenAI's GPT-3 model to generate code complexity scores based on provided code snippets.

## Installation

1. Clone the repository:
```bash
  git clone https://github.com/suhasml/GitHub-Complexity-Analyser.git
```

2. Install the required dependencies:
```bash
 pip install -r requirements.txt
```

3. Set up your OpenAI API credentials:
- Create an account on the OpenAI platform (https://platform.openai.com).
- Obtain your OpenAI API key.
- Set the API key as the value of the `OPENAI_API_KEY` environment variable.

## Usage

1. Run the application:
```bash
  streamlit run app.py
```

2. Enter a GitHub URL to analyze the repositories. The tool will fetch the repositories, preprocess the code files, and generate complexity scores.

3. The tool will display the most complex repository along with its complexity score and a justification for why it is considered the most complex.

## Preprocessing Logic

The Code Complexity Analyzer applies the following preprocessing logic to limit the number of tokens being sent to the model:

### Jupyter Notebook Files

- The code cells within Jupyter notebooks are limited to 200 tokens.

### Package Files

- Package files are limited to 500 tokens.

### Regular Files

- Regular files are decoded with the detected encoding, or 'utf-8' if the encoding is unknown.
- The content of regular files is limited to 200 tokens.

## Contributing

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
