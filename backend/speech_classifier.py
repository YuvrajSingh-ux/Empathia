import torch
import torchaudio
import torch.nn as nn
import io

bundle = torchaudio.pipelines.WAV2VEC2_BASE
model = bundle.get_model().eval()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
resampler = torchaudio.transforms.Resample(orig_freq=16000, new_freq=bundle.sample_rate)

# def extract_embedding(file_path: str):
    
#     waveform, sr = torchaudio.load(file_path)

#     if sr != bundle.sample_rate:
#         waveform = resampler(waveform)

#     if waveform.shape[0] > 1:
#         waveform = waveform.mean(dim=0, keepdim=True)

#     waveform = waveform.to(device)

#     with torch.no_grad():
#         features, _ = model.extract_features(waveform)
#         embedding = features[-1].squeeze(0).mean(dim=0)  # [768]

#     return embedding.unsqueeze(0)

def extract_embedding(file_bytes: bytes):
    
    waveform, sr = torchaudio.load(io.BytesIO(file_bytes))

    if sr != bundle.sample_rate:
        waveform = resampler(waveform)

    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    waveform = waveform.to(device)

    with torch.no_grad():
        features, _ = model.extract_features(waveform)
        embedding = features[-1].squeeze(0).mean(dim=0)  # [768]

    return embedding.unsqueeze(0)


class EmotionClassifier(nn.Module):
    def __init__(self, input_dim=768, hidden_dim=256, num_classes=8):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim,hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x):
        return self.net(x)


classifier = EmotionClassifier()
state_dict = torch.load("Speech_Classifier.pth", map_location=device)

if isinstance(state_dict, dict):
    classifier.load_state_dict(state_dict)
else:
    classifier = state_dict  
classifier = classifier.to(device)
classifier.eval()
label_map={0:'neutral',1:'calm',2:'happy',3:'sadness',4:'angry',5:'fearful',6:'disgust',7:'surprise'}

# def predict_speech(file_path: str, label_map=label_map, top_k=2):

#     embedding = extract_embedding(file_path).to(device)  # [1,768]
    
#     with torch.no_grad():
#         logits = classifier(embedding)  # [1, num_classes]
#         probs = torch.softmax(logits, dim=-1)

#         top_probs, top_indices = torch.topk(probs, k=top_k, dim=-1)

#     results = []
#     for i in range(top_k):
#         idx = top_indices[0, i].item()
#         conf = top_probs[0, i].item()*100
#         label = label_map[idx] if label_map else idx
#         results.append((label, round(conf,2)))

#     return results


def predict_speech(file_bytes: bytes, label_map=label_map, top_k=2):

    embedding = extract_embedding(file_bytes).to(device)  # [1,768]
    
    with torch.no_grad():
        logits = classifier(embedding)  # [1, num_classes]
        probs = torch.softmax(logits, dim=-1)

        top_probs, top_indices = torch.topk(probs, k=top_k, dim=-1)

    results = []
    for i in range(top_k):
        idx = top_indices[0, i].item()
        conf = top_probs[0, i].item()*100
        label = label_map[idx] if label_map else idx
        results.append((label, round(conf,2)))

    return results