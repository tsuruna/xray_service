from argparse import ArgumentParser
from time import time
from datetime import datetime
from reportportal_client import ReportPortalServiceAsync

import csv
import uuid as u
import os

DEFAULT_LAUNCH_NAME = 'Launch_at ' + str(time())
DEFAULT_STATUS = 'SKIPPED'
STATUS_MAPPING = {
    'PASS': 'PASSED',
    'FAIL': 'FAILED',
    'SKIP': 'SKIPPED',
    'TODO': 'SKIPPED'
}


def timestamp():
    return str(int(time() * 1000))


def cvstime_to_timestamp(csv_time):
    utc_dt = datetime.strptime(csv_time, '%d-%m-%Y %H:%M')
    return int(utc_dt.timestamp() * 1000)


def clean_cvs_file(file_in, file_out):
    with open(file_in, encoding='utf-8') as f_in, open(file_out, 'w+', encoding='utf-8') as f_out:
        for line in f_in:
            f_out.write(line.rstrip(';\n') + '\n')


def clean_csv_header(data):
    return {
        k.lstrip(): v
        for k, v in data.items()
    }


def start_timestamp(data):
    if data["Start"]:
        return cvstime_to_timestamp(data["Start"])
    else:
        return timestamp()


def finish_timestamp(data):
    if data["Finish"]:
        return cvstime_to_timestamp(data["Finish"])
    elif data["Start"]:
        return cvstime_to_timestamp(data["Start"])
    else:
        return timestamp()


def read_test_run_from_cvs(file_obj):
    """
    Read a CSV file using csv.DictReader
    """
    return [
        clean_csv_header(line)
        for line in csv.DictReader(file_obj, delimiter=';')
    ]


def main(file, endpoint, uuid, project, tags):
    clean_file = str(u.uuid4())
    clean_cvs_file(file, clean_file)
    with open(clean_file.format(file), encoding='utf-8') as f_obj:
        test_run_data = read_test_run_from_cvs(f_obj)
        print(test_run_data)
        print(test_run_data[0].get('Test Execution Key', DEFAULT_LAUNCH_NAME))
    launch_finish, *_ = sorted(test_run_data, key=lambda x: x['Finish'])
    launch_start, *_ = sorted(test_run_data, key=lambda x: x['Start'])
    os.remove(clean_file)
    service = ReportPortalServiceAsync(
        endpoint=endpoint,
        project=project,
        token=uuid
    )

    service.start_launch(
        name=test_run_data[0].get('Test Execution Key', DEFAULT_LAUNCH_NAME),
        start_time=start_timestamp(launch_start)
    )

    for test in test_run_data:
        test['Status'] = STATUS_MAPPING.get(test['Status'], DEFAULT_STATUS)

        service.start_test_item(
            name=test.get('Test Key'),
            description=None,
            tags=tags,
            start_time=start_timestamp(test),
            item_type="STEP",
            parameters= {
                "Defects": test.get('Defects issues keys'),
                "Executed By": test.get('Executed By')
            }
        )
        if test['Status'] == 'FAILED' and test.get('Defects issues keys'):
            service.log(
                time=finish_timestamp(test),
                message='Known defects for test: {}'.format(test.get('Defects issues keys')),
                level="INFO"
            )
        if test.get('Comment'):
            service.log(
                time=finish_timestamp(test),
                message=str(test.get('Comment')),
                level="WARN"
            )
        service.finish_test_item(end_time=finish_timestamp(test), status=test['Status'])

    # Finish launch.
    service.finish_launch(end_time=finish_timestamp(launch_finish))

    # Due to async nature of the service we need to call terminate() method which
    # ensures all pending requests to server are processed.
    # Failure to call terminate() may result in lost data.
    service.terminate()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-f', '--file', required=True)
    parser.add_argument('-e', '--endpoint', required=True)
    parser.add_argument('-u', '--uuid', required=True)
    parser.add_argument('-p', '--project', required=True)
    parser.add_argument('-t', '--tags', required=False, default=[])
    parser.add_argument('-l', '--launch_name', required=False, default='Launch name')
    args = parser.parse_args()
    main(args.file, args.endpoint, args.uuid, args.project, args.tags)
