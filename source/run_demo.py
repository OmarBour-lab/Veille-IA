from veille_agents import run_pipeline


if __name__ == "__main__":
    result = run_pipeline(use_live=True, use_llm=True)
    print("Pipeline execute avec succes.")
    print(result)
