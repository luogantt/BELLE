import time

import torch
import torch.nn as nn

from gptq import *
from modelutils import *
from quant import *

from transformers import AutoTokenizer
import sys
import json
#import lightgbm as lgb
import logging
import tornado.escape
import tornado.ioloop
import tornado.web
import traceback
DEV = torch.device('cuda:0')

def get_bloom(model):
    import torch
    def skip(*args, **kwargs):
        pass
    torch.nn.init.kaiming_uniform_ = skip
    torch.nn.init.uniform_ = skip
    torch.nn.init.normal_ = skip
    from transformers import BloomForCausalLM
    model = BloomForCausalLM.from_pretrained(model, torch_dtype='auto')
    model.seqlen = 2048
    return model

def load_quant(model, checkpoint, wbits, groupsize):
    from transformers import BloomConfig, BloomForCausalLM 
    config = BloomConfig.from_pretrained(model)
    def noop(*args, **kwargs):
        pass
    torch.nn.init.kaiming_uniform_ = noop 
    torch.nn.init.uniform_ = noop 
    torch.nn.init.normal_ = noop 

    torch.set_default_dtype(torch.half)
    transformers.modeling_utils._init_weights = False
    torch.set_default_dtype(torch.half)
    model = BloomForCausalLM(config)
    torch.set_default_dtype(torch.float)
    model = model.eval()
    layers = find_layers(model)
    for name in ['lm_head']:
        if name in layers:
            del layers[name]
    make_quant(model, layers, wbits, groupsize)

    print('Loading model ...')
    if checkpoint.endswith('.safetensors'):
        from safetensors.torch import load_file as safe_load
        model.load_state_dict(safe_load(checkpoint))
    else:
        model.load_state_dict(torch.load(checkpoint,map_location=torch.device('cuda')))
    model.seqlen = 2048
    print('Done.')

    return model


import argparse
from datautils import *

parser = argparse.ArgumentParser()

parser.add_argument(
    'model', type=str,
    help='llama model to load'
)
parser.add_argument(
    '--wbits', type=int, default=16, choices=[2, 3, 4, 8, 16],
    help='#bits to use for quantization; use 16 for evaluating base model.'
)
parser.add_argument(
    '--groupsize', type=int, default=-1,
    help='Groupsize to use for quantization; default uses full row.'
)
parser.add_argument(
    '--load', type=str, default='',
    help='Load quantized model.'
)

parser.add_argument(
    '--text', type=str,
    help='hello'
)

parser.add_argument(
    '--min_length', type=int, default=10,
    help='The minimum length of the sequence to be generated.'
)

parser.add_argument(
    '--max_length', type=int, default=1024,
    help='The maximum length of the sequence to be generated.'
)

parser.add_argument(
    '--top_p', type=float , default=0.95,
    help='If set to float < 1, only the smallest set of most probable tokens with probabilities that add up to top_p or higher are kept for generation.'
)

parser.add_argument(
    '--temperature', type=float, default=0.8,
    help='The value used to module the next token probabilities.'
)

args = parser.parse_args()

if type(args.load) is not str:
    args.load = args.load.as_posix()

if args.load:
    model = load_quant(args.model, args.load, args.wbits, args.groupsize)
else:
    model = get_bloom(args.model)
    model.eval()
    
model.to(DEV)
tokenizer = AutoTokenizer.from_pretrained(args.model)
print("Human:")

inputs = 'Human: ' +'hello' + '\n\nAssistant:'
input_ids = tokenizer.encode(inputs, return_tensors="pt").to(DEV)
"""
with torch.no_grad():
    generated_ids = model.generate(
        input_ids,
        do_sample=True,
        min_length=args.min_length,
        max_length=args.max_length,
        top_p=args.top_p,
        temperature=args.temperature,
    )
print("Assistant:\n") 
print(tokenizer.decode([el.item() for el in generated_ids[0]])[len(inputs):]) # generated_ids开头加上了bos_token,需要将inpu的内容截断,只输出Assistant 
print("\n-------------------------------\n")

"""
#python bloom_inference.py BELLE_BLOOM_GPTQ_4BIT  --temperature 1.2  --wbits 4 --groupsize 128 --load  BELLE_BLOOM_GPTQ_4BIT/bloom7b-2m-4bit-128g.pt
class GateAPIHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.set_header("Content-Type", "application/text")
        self.set_header("Access-Control-Allow-Origin", "*")


    async def post(self):

        print("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
        postArgs = self.request.body_arguments

        print( postArgs)
        if (not 'status' in postArgs):
            return tornado.web.HTTPError(400)
        try:
            json_str = postArgs.get("status")[0]
#            req = json.loads(json_str)
            print(json_str)
            #logging.error("recieve time : {0} . player id : {1}".format(str(time.time()), str(req["playerID"])))
            inputs = 'Human: ' +json_str.decode('utf-8') + '\n\nAssistant:'
            input_ids = tokenizer.encode(inputs, return_tensors="pt").to(DEV)
            
            with torch.no_grad():
                generated_ids = model.generate(
                    input_ids,
                    do_sample=True,
                    min_length=args.min_length,
                    max_length=args.max_length,
                    top_p=args.top_p,
                    temperature=args.temperature,
                )
            print("Assistant:\n")
            answer=tokenizer.decode([el.item() for el in generated_ids[0]])[len(inputs):]
            print(answer) # generated_ids开头加上了bos_token,需要将inpu的内容截断,只输出Assistant 
            result = {'belle':answer}
            pred_str = str(json.dumps(result))
            self.write(pred_str)
            #logging.error("callback time : {0} . player id : {1}, result:{2}".format(str(time.time()), str(playerID), pred_str))
        except Exception as e:
            logging.error("Error: {0}.".format(e))
            traceback.print_exc()
            raise tornado.web.HTTPError(500)

    def get(self):
        raise tornado.web.HTTPError(300)


import logging
import tornado.autoreload
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpserver
#import   itempredict
import argparse
from tornado.httpserver import HTTPServer

def trace():
    from config import path_dir  as prr
    import datetime
    import pandas as pd
    rhh=prr()
    stamp0=datetime.datetime.now()
    stamp1=stamp0.strftime("%Y-%m-%d %H:%M:%S")
    stamp2=pd.DataFrame([[stamp1]],columns=['stamp'])
    stamp2.to_csv(rhh+'/service_start.csv',index=False)
    



#trace()
if __name__ == "__main__":
    tornado.options.define("port", default=8081,type=int, help="This is a port number",
                           metavar=None, multiple=False, group=None, callback=None)
    tornado.options.parse_command_line()
    app = tornado.web.Application([
        (r"/", GateAPIHandler),
    ])
    apiport = tornado.options.options.port
    app.listen(apiport)
    logging.info("Start Gate API server on port {0}.".format(apiport))

    server = HTTPServer(app)
    server.start(1)
    #trace()
    #tornado.autoreload.start()
    tornado.ioloop.IOLoop.instance().start()
                                             

