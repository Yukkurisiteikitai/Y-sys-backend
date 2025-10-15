import json
with open("sample_test_data.json","r",encoding="utf-8")as f:
	data = json.load(f)

print(data)
print(data["sample_experience_data"])
