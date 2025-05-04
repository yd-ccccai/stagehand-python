import asyncio
import importlib
import os
import sys
from typing import Optional, List

from evals.utils import setup_environment


class SimpleLogger:
    def __init__(self):
        self._logs = []

    def info(self, message):
        self._logs.append(message)
        print("INFO:", message)

    def error(self, message):
        self._logs.append(message)
        print("ERROR:", message)

    def get_logs(self):
        return self._logs


async def run_observe_eval(eval_name: str, model_name: Optional[str] = None) -> dict:
    """
    Run a specific observe eval by name.
    
    Args:
        eval_name: Name of the eval to run (e.g., "taxes" for observe_taxes)
        model_name: Name of the model to use (defaults to environment variable or gpt-4o)
    
    Returns:
        Result of the evaluation
    """
    # Set up environment variables
    setup_environment()
    
    # Determine model name to use
    if not model_name:
        model_name = os.getenv("MODEL_NAME") or os.getenv("OPENAI_MODEL") or "gpt-4o"
    print(f"Using model: {model_name}")
    
    # Construct module path
    if eval_name.startswith("observe_"):
        # User provided full name
        module_name = eval_name
    else:
        # User provided short name
        module_name = f"observe_{eval_name}"
    
    module_path = f"evals.observe.{module_name}"
    
    try:
        # Import the module
        module = importlib.import_module(module_path)
        
        # Get the function with the same name as the file
        if hasattr(module, module_name):
            func = getattr(module, module_name)
            
            # Create logger
            logger = SimpleLogger()
            
            # Run the eval
            print(f"Running {module_path}...")
            result = await func(model_name, logger)
            
            # Print result summary
            success = result.get("_success", False)
            status = "SUCCESS" if success else "FAILURE"
            print(f"\nResult: {status}")
            
            if not success and "error" in result:
                print(f"Error: {result['error']}")
                
            return result
        else:
            print(f"Error: Could not find function {module_name} in module {module_path}")
            return {"_success": False, "error": f"Function {module_name} not found"}
    except ImportError as e:
        print(f"Error: Could not import module {module_path}: {e}")
        return {"_success": False, "error": f"Module {module_path} not found"}
    except Exception as e:
        print(f"Error running {module_path}: {e}")
        return {"_success": False, "error": str(e)}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run a specific observe eval")
    parser.add_argument("eval_name", help="Name of the eval to run (e.g., 'taxes' for observe_taxes)")
    parser.add_argument("--model", type=str, help="Model name to use")
    args = parser.parse_args()
    
    asyncio.run(run_observe_eval(args.eval_name, args.model)) 