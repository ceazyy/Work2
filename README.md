# Verilog Code Analyzer and LaTeX Documentation Generator

This tool analyzes Verilog HDL files using Azure OpenAI's GPT models and generates comprehensive specification documentation in LaTeX format.

## Features

- **Automated Verilog Analysis**: Uses Azure OpenAI GPT models to deeply analyze Verilog code
- **LaTeX Documentation**: Generates professional specification documents using your template
- **Configurable Analysis**: Customizable analysis depth and sections
- **Multiple Module Support**: Processes multiple Verilog files simultaneously
- **Professional Output**: Academic-style documentation suitable for research projects

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Azure OpenAI**:
   - Option 1: Set environment variables:
     ```bash
     export AZURE_OPENAI_API_KEY="your-api-key-here"
     export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
     ```
   - Option 2: Edit `config.yaml` and replace the placeholders with your actual values

3. **Update Project Information**:
   Edit `config.yaml` to include your project details:
   ```yaml
   project_info:
     student_name: "Your Name"
     student_number: "12345678"
     research_centre: "Your Research Centre"
     project_title: "Your Project Title"
     supervisor: "Dr. Your Supervisor"
   ```

## Usage

### Basic Usage

Place your Verilog files in the `input/` directory and run:

```bash
python verilog_analyzer.py
```

This will:
1. Analyze all `.v` files in the `input/` directory
2. Generate comprehensive analysis using GPT-4o-mini
3. Create `specification_document.tex` using your template

### Advanced Usage

You can also use the analyzer programmatically:

```python
from verilog_analyzer import VerilogAnalyzer

# Initialize analyzer
analyzer = VerilogAnalyzer("config.yaml")

# Run complete analysis
analyzer.run_complete_analysis(
    input_dir="input/",
    template_path="template.tex",
    output_path="my_specification.tex"
)
```

## Configuration

The `config.yaml` file allows you to customize:

- **Azure OpenAI Settings**: Deployment name, endpoint, API version, temperature, token limits
- **Project Information**: Student details, project title, supervisor
- **Analysis Depth**: Comprehensive, detailed, or basic analysis
- **Output Sections**: Which analysis sections to include
- **File Processing**: Input/output directories and file extensions

## Analysis Sections

The tool can generate analysis covering:

- **Functionality Overview**: High-level module description
- **Module Interface**: Detailed port and parameter analysis
- **Behavioral Description**: Internal logic and behavior
- **Timing Analysis**: Clock domains and synchronization
- **Design Patterns**: Coding practices and patterns used
- **Potential Improvements**: Optimization suggestions
- **Test Considerations**: Verification strategies

## Output

The generated LaTeX document includes:

1. **Project Summary**: Overview of objectives and accomplishments
2. **Research Plan**: Short-term and long-term goals
3. **Module Analysis**: Detailed technical analysis of each Verilog module
4. **Professional Formatting**: Academic-style documentation

## Example Verilog Modules Analyzed

The tool has been tested with various Verilog modules including:

- **4-bit Counter**: Synchronous counter with reset
- **D Flip-Flop**: Basic sequential logic element
- **LIFO Stack**: Parameterized stack implementation
- **JK Flip-Flop**: JK flip-flop with case-based logic

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your Azure OpenAI API key and endpoint are properly set
2. **No Modules Found**: Check that `.v` files are in the correct input directory
3. **LaTeX Errors**: Verify that your template file is properly formatted

### Debugging

Enable detailed logging by modifying the logging level in the script:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Requirements

- Python 3.7+
- Azure OpenAI API key and endpoint
- LaTeX distribution (for compiling the generated document)

## License

This tool is provided as-is for educational and research purposes.
