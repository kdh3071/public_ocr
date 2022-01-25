# -*- coding: utf-8 -*-
import torch
import json
import os
import datetime
from PIL import Image
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class AttnLabelConverter(object):
    """ Convert between text-label and text-index """

    def __init__(self, character):
        # character (str): set of the possible characters.
        # [GO] for the start token of the attention decoder. [s] for end-of-sentence token.
        list_token = ['[GO]', '[s]']  # ['[s]','[UNK]','[PAD]','[GO]']
        list_character = list(character)
        self.character = list_token + list_character

        self.dict = {}
        for i, char in enumerate(self.character):
            # print(i, char)
            self.dict[char] = i

    def encode(self, text, batch_max_length=25):
        """ convert text-label into text-index.
        input:
            text: text labels of each image. [batch_size]
            batch_max_length: max length of text label in the batch. 25 by default

        output:
            text : the input of attention decoder. [batch_size x (max_length+2)] +1 for [GO] token and +1 for [s] token.
                text[:, 0] is [GO] token and text is padded with [GO] token after [s] token.
            length : the length of output of attention decoder, which count [s] token also. [3, 7, ....] [batch_size]
        """
        length = [len(s) + 1 for s in text]  # +1 for [s] at end of sentence.
        # batch_max_length = max(length) # this is not allowed for multi-gpu setting
        batch_max_length += 1
        # additional +1 for [GO] at first step. batch_text is padded with [GO] token after [s] token.
        batch_text = torch.LongTensor(len(text), batch_max_length + 1).fill_(0)
        for i, t in enumerate(text):
            text = list(t)
            text.append('[s]')
            text = [self.dict[char] for char in text]
            batch_text[i][1:1 + len(text)] = torch.LongTensor(text)  # batch_text[:, 0] = [GO] token
        return (batch_text.to(device), torch.IntTensor(length).to(device))

    def decode(self, text_index, length):
        """ convert text-index into text-label. """
        texts = []
        for index, l in enumerate(length):
            text = ''.join([self.character[i] for i in text_index[index, :]])
            texts.append(text)
        return texts

def make_json(img_path,pred_text_list,xywh):
    img = Image.open(img_path)
    width, height = img.size

    result = {'images': [{"image.make.code": os.path.basename(img_path).split('-')[0],
                          "image.make.year": os.path.basename(img_path).split('-')[1],
                          "image.category": 'None',
                          "image.width": width,
                          "image.height": height,
                          "image.file.name": os.path.basename(img_path),
                          "image.create.time": datetime.datetime.today().strftime(
                              '%Y-%m-%d %H:%M:%S')}],  # datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')

              'annotations': [{'id': 0,
                               'annotation.type': 'rectangle',
                               "annotation.text": pred_text_list[0],
                               "annotation.bbox": [int(xywh[0][0]), int(xywh[0][1]), int(xywh[0][2]), int(xywh[0][3])]}]}

    for idx in range(1,len(pred_text_list)):
        result['annotations'].append({'id': '{}'.format(idx + 1), 'annotation.type': 'rectangle',
                                      "annotation.text": pred_text_list[idx],
                                      "annotation.bbox": [int(xywh[idx][0]), int(xywh[idx][1]), int(xywh[idx][2]), int(xywh[idx][3])]})

    with open(f"./json/{os.path.basename(img_path)[:-4]}.json", 'w', encoding='utf-8') as outfile:
        json.dump(result, outfile, indent=4, ensure_ascii=False)
    print("json saved!")
    img.close()
