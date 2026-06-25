import torch
import torch.nn as nn
from transformers import DistilBertTokenizer, DistilBertModel
import re

def convert_lower(text):
    text = re.sub(r"[=\[]", "", text) 
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()

class Classifier(nn.Module):
  def __init__(self,embedding):
    super().__init__()
    self.embedding=embedding
    for param in self.embedding.parameters():
            param.requires_grad = False
    self.classifier=nn.Sequential(
        nn.Linear(768,256),
        nn.BatchNorm1d(256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256,6)
    )
  def forward(self,input_ids,attention_mask):
    output=self.embedding(input_ids=input_ids,attention_mask=attention_mask)
    output=output.last_hidden_state[:,0,:]
    output=self.classifier(output)
    return output


tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
embedding=DistilBertModel.from_pretrained('distilbert-base-uncased')
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
classifier = Classifier(embedding)
state_dict = torch.load("text_classifier_model.pt", map_location=device)

if isinstance(state_dict, dict):
    classifier.load_state_dict(state_dict)
else:
    classifier = state_dict

classifier = classifier.to(device)
classifier.eval()
label_map={0:'sadness',1:'joy',2:'love',3:'anger',4:'fearful',5:'surprise'}

def predict_text(text: str, label_map=label_map, top_k=1):

    text = convert_lower(text)

    inputs = tokenizer(
        text,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=128
    ).to(device)

    with torch.no_grad():
        logits = classifier(inputs["input_ids"], inputs["attention_mask"])
        probs = torch.softmax(logits, dim=-1)

        top_probs, top_indices = torch.topk(probs, k=top_k, dim=-1)

    results = []
    for i in range(top_k):
        idx = top_indices[0, i].item()
        conf = top_probs[0, i].item()*100
        label = label_map[idx] if label_map else idx
        results.append((label, round(conf,2)))

    return results
