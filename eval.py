import argparse
import numpy as np

def define_arguments():
    p = argparse.ArgumentParser()
    
    p.add_argument('--inference_result',type=str,required=True)
    p.add_argument('--save_path',type=str,required=True)
    p.add_argument('--language',type=str,required=True)
    
    args = p.parse_args()
    
    return args

args = define_arguments()


import json
with open(args.inference_result,'r') as f:
    data=json.load(f)


### KMS - Keyword Matching Score ###
win=0
for index in range(len(data)):
    data[index]['result'] = data[index]['result'].lower().replace('<|eot_id|>','').strip()
    main_key1 = data[index]['answer_keyword1'].lower()
    main_key2 = data[index]['answer_keyword2'].lower()
    if main_key1 in data[index]['result'] and main_key2 in data[index]['result']:
        win+=1
    else:
        continue
### KMS - Keyword Matching Score ###


### ROUGE,BERTScore score ###
import evaluate
from transformers import AutoTokenizer
rouge = evaluate.load('rouge')
bleu = evaluate.load('bleu')
bertscore = evaluate.load("bertscore")

pred=[data[i]['result'] for i in range(len(data))]
label = [data[i]['label'] for i in range(len(data))]


if args.inference_result in 'qwenvlchat':
    tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen-VL-Chat')
# This code loads the tokenizer based on model name and can be customized for your specific needs.

elif args.inference_result in 'gpt4o':
    import tiktoken
    encoding_name = tiktoken.encoding_for_model("gpt-4o").name
    encoding = tiktoken.get_encoding(encoding_name)
    def tokenizer(x):
        return encoding.encode(x)

bert_score =bertscore.compute(predictions=pred, references=label,lang=args.language,model_type="bert-base-multilingual-cased")
rouge_score = rouge.compute(predictions=pred, references=label,tokenizer=lambda x: tokenizer(x)['input_ids'])
bleu_score = bleu.compute(predictions=pred, references=label,tokenizer=lambda x: tokenizer(x)['input_ids'])
### ROUGE,BERTScore score ###


######### SAVE ##########
result = {
    'KMS' : win/300,
    'Bertscore-f1' : np.mean(bert_score['f1']),
    'ROUGE-1' : rouge_score['rouge1'],
    'ROUGE-2' : rouge_score['rouge2'],
    'ROUGE-L' : rouge_score['rougeL'],
    'ROUGE-Lsum' : rouge_score['rougeLsum'],
    'BLEU': bleu_score['bleu'],
    'model':args.inference_result.split('/')[-1].split('.')[0]
}

with open(args.save_path,'w') as f:
    json.dump(result,f,indent=4,ensure_ascii=False)
######### SAVE ##########
