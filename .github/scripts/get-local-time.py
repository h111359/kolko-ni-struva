#!/usr/bin/env python3
import datetime

def main():
    now = datetime.datetime.now()
    print(now.strftime('%Y%m%d-%H%M'))

if __name__ == '__main__':
    main()
