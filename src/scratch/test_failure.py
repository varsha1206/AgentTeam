from pathlib import Path

from agentteam.evaluation.test_injection import get_injection, set_injection

ws = Path(r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace")
set_injection(ws, "eval_dataset_1.csv", "syntax_error")

print((ws / ".eval_injection.json").exists())  # should be True
print((ws / ".eval_injection.json").read_text())  # should show the JSON
print(get_injection(ws, "eval_dataset_1.csv"))  # should print "syntax_error"
