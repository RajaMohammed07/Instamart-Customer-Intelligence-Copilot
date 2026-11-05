from __future__ import annotations

from src.part_d.policy_retrieval import answer


def main():
    q = 'What refund is available if delivery exceeds 45 minutes?'
    res = answer(q)
    print(res)
    return res


if __name__ == '__main__':
    main()
