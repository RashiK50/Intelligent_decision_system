# Enterprise Decision Intelligence Platform

A multi-agent AI system that converts natural language business questions into actionable insights using LangGraph, Gemini, FastAPI, and PostgreSQL.

## Workflow

```text
User Query
    ↓
Guardrail Agent
    ↓
Intent Agent
    ↓
Planner Agent
    ↓
SQL Generator Agent
    ↓
SQL Validator Agent
    ↓
Database Executor Agent
    ↓
Output Agent
    ↓
Business Insight
```

## Features

* Multi-Agent Architecture with LangGraph
* Natural Language to SQL
* Schema-Aware Planning
* SQL Validation
* Business Insight Generation
* Automatic Schema Extraction
* Prompt Versioning
* FastAPI + Swagger Integration
* PostgreSQL (Supabase) Support

## Tech Stack

* Python
* LangGraph
* LangChain
* FastAPI
* Gemini
* PostgreSQL
* Supabase
* Pydantic

## Running the Project

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Swagger UI:

```text
http://localhost:8000/docs
```

## Example Query

```json
{
  "query": "What are the top selling products?"
}
```

## Project Structure

```text
agents/
api/
database/
graph/
prompts/
registry/
state/
tests/
tools/
utils/
```

## Current Status

 Intent Agent
 Planner Agent
 SQL Generator Agent
 SQL Validator Agent
 Database Executor Agent
 Output Agent
 Guardrail Agent
 LangGraph Integration
 Prompt Versioning
 FastAPI + Swagger

## Future Improvements

* Orchestrator Agent
* Dynamic Workflow Selection
* Forecasting Workflow
* Visualization Agent
* LLM-Based Guardrails
* KPI Dashboards

## Resume Summary

Built a Multi-Agent Enterprise Decision Intelligence Platform using LangGraph, FastAPI, Gemini, PostgreSQL, and Supabase with schema-aware planning, text-to-SQL generation, SQL validation, and business insight generation.
