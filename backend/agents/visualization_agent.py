"""
JARVIS — Visualization Agent
Generates beautiful charts, graphs, and dashboards.
"""

import os
import json
import time
import matplotlib
matplotlib.use('Agg')  # Headless mode for matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from backend.agents.base import BaseAgent
from backend.config import llm, GENERATED_IMAGES_DIR
from backend.logger import get_logger

logger = get_logger("agents.visualization")


class ChartSpec(BaseModel):
    chart_type: str = Field(description="Type of chart: 'bar', 'line', 'pie', 'area', or 'scatter'")
    title: str = Field(description="Descriptive title of the chart")
    x_label: str = Field(description="Label for the X-axis")
    y_label: str = Field(description="Label for the Y-axis")
    data: list[dict] = Field(description="List of dictionaries representing data points. E.g. [{'label': 'Jan', 'value': 200}, {'label': 'Feb', 'value': 400}]")
    x_key: str = Field(description="The key in the data dictionaries to use for the X-axis (e.g. 'label')")
    y_keys: list[str] = Field(description="List of keys in the data dictionaries to use for the Y-axis values (e.g. ['value'])")


class VisualizationAgent(BaseAgent):
    name = "visualization"
    description = (
        "Generate charts, graphs, and visual dashboards from datasets, "
        "tables, or lists of numbers. Input a description of the data or numbers "
        "and specify the desired chart type (bar, line, pie, area, scatter)."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Visualization Agent with query: {query[:80]}...")

        # Step 1: Use LLM to structure the query into a charting specification
        parser = JsonOutputParser(pydantic_object=ChartSpec)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert data analyst and visualization specialist. "
                "Analyze the user query and extract the data to be visualized. "
                "If the query doesn't specify a chart type, choose the most appropriate one (bar for categories, line for time-series, pie for distributions, etc.). "
                "Output a clean JSON object representing the chart specification following this schema:\n{format_instructions}",
            ),
            ("human", "{query}"),
        ]).partial(format_instructions=parser.get_format_instructions())

        try:
            chain = prompt | llm | parser
            spec = chain.invoke({"query": query})
        except Exception as e:
            logger.error(f"Failed to parse chart spec: {e}")
            return f"Error: Visualization Agent failed to parse data structure. Details: {str(e)}"

        chart_type = spec.get("chart_type", "bar").lower()
        title = spec.get("title", "Data Visualization")
        x_label = spec.get("x_label", "X-Axis")
        y_label = spec.get("y_label", "Y-Axis")
        data = spec.get("data", [])
        x_key = spec.get("x_key", "label")
        y_keys = spec.get("y_keys", ["value"])

        if not data:
            return "Error: Visualization Agent could not extract any valid data points from the query."

        logger.info(f"Parsed chart spec: {chart_type} chart '{title}' with {len(data)} points.")

        # Step 2: Render Matplotlib image as a fallback/static copy
        filename = f"chart_{int(time.time())}.png"
        save_path = os.path.join(GENERATED_IMAGES_DIR, filename)

        try:
            # Set styled theme for matplotlib
            sns.set_theme(style="darkgrid")
            plt.figure(figsize=(10, 6))

            # Dark theme adjustments
            plt.rcParams['figure.facecolor'] = '#0c0c1d'
            plt.rcParams['axes.facecolor'] = '#111128'
            plt.rcParams['text.color'] = '#e8eaff'
            plt.rcParams['axes.labelcolor'] = '#8b8fad'
            plt.rcParams['xtick.color'] = '#8b8fad'
            plt.rcParams['ytick.color'] = '#8b8fad'
            plt.rcParams['grid.color'] = '#3a2d54'

            # Extract data lists
            x_vals = [d.get(x_key, "") for d in data]
            colors = sns.color_palette("muted", len(y_keys))

            if chart_type == "pie":
                # Pie chart only uses the first y_key
                y_key = y_keys[0]
                y_vals = [float(d.get(y_key, 0)) for d in data]
                plt.pie(y_vals, labels=x_vals, autopct='%1.1f%%', startangle=140, colors=sns.color_palette("coolwarm", len(data)))
            else:
                for idx, y_key in enumerate(y_keys):
                    y_vals = [float(d.get(y_key, 0)) for d in data]
                    label = y_key if len(y_keys) > 1 else y_label

                    if chart_type == "line":
                        plt.plot(x_vals, y_vals, marker='o', linewidth=2.5, color=colors[idx], label=label)
                    elif chart_type == "area":
                        plt.fill_between(x_vals, y_vals, alpha=0.3, color=colors[idx])
                        plt.plot(x_vals, y_vals, marker='o', linewidth=2, color=colors[idx], label=label)
                    elif chart_type == "scatter":
                        plt.scatter(x_vals, y_vals, s=100, color=colors[idx], label=label)
                    else:  # bar
                        plt.bar(x_vals, y_vals, alpha=0.8, color=colors[idx], label=label)

                if chart_type != "area" and len(y_keys) > 1:
                    plt.legend()

                plt.xlabel(x_label)
                plt.ylabel(y_label)

            plt.title(title, fontsize=14, fontweight='bold', pad=15)
            plt.tight_layout()
            plt.savefig(save_path, dpi=150, facecolor='#0c0c1d')
            plt.close()

            logger.info(f"Matplotlib chart saved successfully to {save_path}")

        except Exception as e:
            logger.error(f"Failed to generate Matplotlib chart image: {e}")
            # Non-blocking: we still have the frontend interactive specs, but log the error
            save_path = None

        # Step 3: Format the JSON string for the frontend Recharts rendering
        frontend_spec = {
            "type": chart_type,
            "title": title,
            "xLabel": x_label,
            "yLabel": y_label,
            "xKey": x_key,
            "yKeys": y_keys,
            "data": data
        }

        # Step 4: Return dual-format output
        relative_url = f"/images/{filename}" if save_path else None
        
        result_message = f"📊 **{title}**\n\n"
        result_message += f"Here is the visualization of your requested data:\n\n"
        
        # Interactive charting block
        result_message += f"```chart\n{json.dumps(frontend_spec, indent=2)}\n```\n\n"
        
        # Fallback image block
        if relative_url:
            result_message += f"![Chart Fallback]({relative_url})\n"
            result_message += f"*Generated chart saved to: `{save_path}`*"
            
        return result_message
