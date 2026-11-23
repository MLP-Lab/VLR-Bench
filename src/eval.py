import os
import json
import argparse
import re
import numpy as np
import evaluate
from transformers import AutoTokenizer

'''
The JSON file containing the inference results of the model to be evaluated must include the following values:

'result': The model's inference output.
'label': The output value from MLP-KTLim/VLR-Bench.
'answer_keyword1': The keyword1 value from MLP-KTLim/VLR-Bench.
'answer_keyword2': The keyword2 value from MLP-KTLim/VLR-Bench.
'''

def define_arguments():
    p = argparse.ArgumentParser()
    
    p.add_argument('--inference_result',type=str,required=True)
    p.add_argument('--save_path',type=str,required=True)
    p.add_argument('--language',type=str,required=True)
    p.add_argument('--tokenizer',type=str,default=None,
                   help="Tokenizer used by ROUGE and BLEU: a Hugging Face model id, or 'tiktoken:<model>' "
                        "(e.g. 'tiktoken:gpt-4o'). If omitted, it is chosen from the inference_result "
                        "filename (see TOKENIZERS below).")
    p.add_argument('--lowercase_pred',action='store_true',
                   help="Reproduce the protocol used for Table 1 of the paper: predictions are lowercased "
                        "before ROUGE, BLEU and BERTScore, while references keep their original casing. "
                        "By default, prediction casing is preserved.")

    args = p.parse_args()
    
    return args

args = define_arguments()

with open(args.inference_result,'r') as f:
    data=json.load(f)

### KMS - Keyword Matching Score ###
win=0
for index in range(len(data)):
    result = data[index]['result']
    result_lower = result.lower().replace('<|eot_id|>', '').strip()
    data[index]['result'] = re.sub(r'<\|eot_id\|>', '', result, flags=re.IGNORECASE | re.ASCII).strip()
    data[index]['result_lower'] = result_lower
    main_key1 = data[index]['answer_keyword1'].lower()
    main_key2 = data[index]['answer_keyword2'].lower()
    if main_key1 in result_lower and main_key2 in result_lower:
        win+=1
    else:
        continue
### KMS - Keyword Matching Score ###


### ROUGE,BERTScore score ###
rouge = evaluate.load('rouge')
bleu = evaluate.load('bleu')
bertscore = evaluate.load("bertscore")

if args.lowercase_pred:
    # Paper (Table 1) protocol: lowercased predictions, original-case references.
    pred = [data[i]['result_lower'] for i in range(len(data))]
else:
    pred = [data[i]['result'] for i in range(len(data))]
label = [data[i]['label'] for i in range(len(data))]


# Tokenizer for ROUGE and BLEU, chosen from the inference_result filename unless --tokenizer is given.
# Add an entry here (filename substring -> tokenizer) to evaluate another model.
TOKENIZERS = {
    'llavallama3': 'xtuner/llava-llama-3-8b-v1_1-transformers',
    'qwenvlchat': 'Qwen/Qwen-VL-Chat',
    'gpt4o': 'tiktoken:gpt-4o',
}
TRUST_REMOTE_CODE = {'Qwen/Qwen-VL-Chat'}

def load_tokenizer(name):
    if name.startswith('tiktoken:'):
        import tiktoken
        encoding = tiktoken.encoding_for_model(name.split(':', 1)[1])
        return lambda x: {'input_ids': encoding.encode(x)}
    # Qwen-VL-Chat ships its tokenizer as custom code; only allow remote code for known repos.
    return AutoTokenizer.from_pretrained(name, trust_remote_code=name in TRUST_REMOTE_CODE)

tokenizer_name = args.tokenizer
if tokenizer_name is None:
    file_name = os.path.basename(args.inference_result)
    matches = [tok for key, tok in TOKENIZERS.items() if key in file_name]
    if len(matches) != 1:
        raise SystemExit(f"Could not choose a tokenizer for '{file_name}' (matches: {matches}). "
                         f"Pass --tokenizer explicitly, or add an entry to TOKENIZERS.")
    tokenizer_name = matches[0]
tokenizer = load_tokenizer(tokenizer_name)

bert_score =bertscore.compute(predictions=pred, references=label,lang=args.language,model_type="bert-base-multilingual-cased")
rouge_score = rouge.compute(predictions=pred, references=label,tokenizer=lambda x: tokenizer(x)['input_ids'])
bleu_score = bleu.compute(predictions=pred, references=label,tokenizer=lambda x: tokenizer(x)['input_ids'])
### ROUGE,BERTScore score ###


######### SAVE ##########
result = {
    'KMS' : win/len(data),
    'Bertscore-f1' : np.mean(bert_score['f1']),
    'ROUGE-1' : rouge_score['rouge1'],
    'ROUGE-2' : rouge_score['rouge2'],
    'ROUGE-L' : rouge_score['rougeL'],
    'ROUGE-Lsum' : rouge_score['rougeLsum'],
    'BLEU': bleu_score['bleu'],
    'model':args.inference_result.split('/')[-1].split('.')[0]
}

save_dir = os.path.dirname(args.save_path)
os.makedirs(save_dir, exist_ok=True)  

with open(args.save_path, 'w') as f:
    json.dump(result, f, indent=4, ensure_ascii=False)
######### SAVE ##########
