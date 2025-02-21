from typing import List, Union
from dataclasses import asdict


def confirm_config(config):
    conf_dict = asdict(config)
    print('Read configuration:')
    for key, value in conf_dict.items():
        print(f'{key}: {value}')
    print('Proceed? (y/n)')
    print(':', end='')
    answer = input()
    answer = answer.strip()
    return answer == 'y'


def read_user_selection(
    text: str,
    options: List[Union[str, int]],
    as_number: bool = True,
) -> Union[str, None]:

    option_idx = list(range(1, len(options)+1))
    while True:
        if as_number:
            print(text)
            for idx, option in zip(option_idx, options):
                print(f'{option}: {idx}')
            print(':', end='')
            answer = input()
            answer = answer.strip()
            if answer == '':
                return None
            try:
                answer_num = int(answer)
                if answer_num not in option_idx:
                    raise Exception
                return options[answer_num-1]
            except Exception:
                print(f'Invalid answer: "{answer}" - should be one of {option_idx}')
        else:
            print(text)
            print(f'{options}\n:', end='')
            answer = input()
            answer = answer.strip()
            if answer == '':
                return None
            if answer not in options:
                print(f'Invalid answer: "{answer}" - should be one of {options}')
                continue
            else:
                return answer
