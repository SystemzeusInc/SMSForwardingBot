"""Processing related to telephone number exclusion lists."""
from typing import List

def get_exclusion_list() -> List[str]:
    """Get exclusion list.

    Returns:
        List[str]: Exclusion list
    """
    with open('../config/exclude_number.txt', 'r') as f:
        data = f.read()
    data = data.strip().split('\n')
    data = sum(list(map(lambda x: x.split(','), data)), [])  # flatten
    return data

def add_exclusion_list(number: str) -> None:
    """Add exclusion list.

    Args:
        number (str): Number to be excluded
    """
    with open('../config/exclude_number.txt', 'a') as f:
        f.write(str(number) + '\n')


def delete_exclusion_list(number: str) -> bool:
    """Delete exclusion list.

    Args:
        number (str): Number to be removed from exclusion list

    Returns:
        bool: False if number does not exist in exclusion list
    """
    data = get_exclusion_list()
    new_data = [d for d in data if d != number]

    if number not in data:
        return False

    with open('../config/exclude_number.txt', 'w') as f:
        for d in new_data:
            f.write(str(d) + '\n')
    return True
