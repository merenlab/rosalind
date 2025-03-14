import re
import sys
import time
import glob
import random
import shutil
import platform
import argparse
import requests
import subprocess
from datetime import datetime
from collections import defaultdict


class SlurmMonitor:
    def __init__(self, args):
        self.args = args

        # user args
        A = lambda x: self.args.__dict__[x] if x in self.args.__dict__ else None
        self.webhook = A('webhook')
        self.group_id = A('group_id')

        self.check_interval = A('squeue_check_interval')
        self.overall_summary_interval = A('overall_summary_interval')
        self.user_jobs_interval = A('user_jobs_interval')

        self.stdout_only = A('stdout_only')
        self.testing = A('testing')

        if self.testing:
            self.stdout_only = True

        # some default variables
        self.previous_users = set([])

        # this shouldn't be here, but I will keep it here until there is a
        # second user of this program :p
        self.known_users = {"tepp5511": "<@U08H4G2UV>", # meren
                            "elgo4396": "<@UCE940CG0>", # iva
                            "patz5242": "<@UDKBXCF1R>", # florian
                            "bube0466": "<@U03N57D5PF0>", # mete
                            "gegu0440": "<@U0677CTPU2J>", # xixi
                            "larm6177": "<@U05A89NS5QT>", # sarah
                            "tele0144": "<@U041JV3L1GX>", # alex
                            "xuaf2725": "<@U05SYDN0QKU>", # katy
                            "sore6591": "<@U06GGGRPZ18>", # avril
                            "jert0988": "<@U0106BK0S3Y>", # amy
                            "zina4710": "<@UHYU10DTK>", # jessika
                            "mueb6691": "Matthias Weitz", # matthias
                            }

        try:
            if not shutil.which("squeue") and not self.testing:
                raise RuntimeError("You don't have `squeue` on this computer to run this program without the `--testing` flag :/")
        except RuntimeError as e:
            print(f"\n\033[91mERROR:\033[0m {e}\n")
            sys.exit(1)

        try:
            if not self.webhook and not self.stdout_only:
                raise RuntimeError("You are running this program without a webhook -- that is fine, but in that case you have to "
                                   "include the flag  `--stdout-only`. BECAUSE.")
        except RuntimeError as e:
            print(f"\n\033[91mERROR:\033[0m {e}\n")
            sys.exit(1)




    @staticmethod
    def parse_time(time_str):
        """Converts time string from various squeue output formats (D-H:M:S, H:M:S, M:S, S) to a human-readable format."""

        if '-' in time_str:
            day, rest = time_str.split('-')
            day = int(day)
            hours, minutes, seconds = list(map(int, rest.split(':')))
        else:
            parts = list(map(int, time_str.split(':')))
            if len(parts) == 3:  # H:M:S format
                hours, minutes, seconds = parts
                days = 0
            elif len(parts) == 2:  # M:S format
                minutes, seconds = parts
                hours = 0
                days = 0
            elif len(parts) == 1:  # S format
                seconds = parts[0]
                minutes = 0
                hours = 0
                days = 0

        readable_time = []
        if days:
            readable_time.append(f"{days}d")
        if hours:
            readable_time.append(f"{hours}h")
        if minutes:
            readable_time.append(f"{minutes}m")
        if seconds:
            readable_time.append(f"{seconds}s")

        return ' '.join(readable_time) if readable_time else "0s"


    def get_random_slack_notification_for_jobs(self, user, event):
        """Generates a random SLURM notification message for Slack for new/finished jobs on ROSA by a given user."""

        new_job_messages = [
            f"There are new jobs on ROSA for *{user}*! Buckle up! :rocket:",
            f"Heads up, *{user}*! Fresh jobs just landed on ROSA! :eyes:",
            f"Hey *{user}*, your jobs just hit the queue! :construction_worker:",
            f"New ROSA jobs incoming for *{user}*! :computer:",
            f"*{user}* has new jobs running on ROSA. :chart_with_upwards_trend:",
            f"Looks like *{user}* is keeping ROSA busy again! :hourglass_flowing_sand:",
            f"Incoming workload detected! *{user}* has jobs in the queue! :robot:",
            f"New jobs for *{user}* on ROSA. :gear:",
            f"Brace yourselves, *{user}*’s jobs are running on ROSA! :zap:",
            f"Guess who’s back? It’s *{user}* with more jobs on ROSA! :sunglasses:",
            f"ROSA’s got work to do! *{user}* just submitted new jobs! :fire:",
            f"Hey *{user}*, your jobs are officially in action on ROSA! :runner:",
            f"New SLURM jobs detected! *{user}* is on a roll? :clipboard:",
            f"Great news: *{user}* has new jobs in ROSA’s pipeline! :brain:",
            f"All systems go! *{user}* has jobs running on ROSA! :rocket:",
            f"New jobs alert! *{user}* is back at it on ROSA! :alarm_clock:",
            f"Time to put ROSA to work! *{user}* just submitted some jobs! :computer:",
            f"Processing request confirmed! *{user}*’s jobs are in the system! :white_check_mark:"
        ]

        finished_job_messages = [
            f"Mission accomplished! All ROSA jobs by *{user}* are done! :tada:",
            f"No more jobs for *{user}*! ROSA can finally take a breather. :relieved:",
            f"*{user}*’s jobs have wrapped up! Time to celebrate! :champagne:",
            f"That’s a wrap! *{user}* has no more jobs on ROSA! :clapper:",
            f"All jobs done! *{user}* can rest easy now. :sleeping:",
            f"ROSA just finished running all jobs by *{user}*! Nice work! :muscle:",
            f"Break time! *{user}*’s jobs are all completed. :coffee:",
            f"All clear! *{user}* has no active jobs on ROSA. :white_check_mark:",
            f"Another batch bites the dust! *{user}* is all done. :boom:",
            f"Processing complete! *{user}*’s jobs are no more! :robot:",
            f"Compute cycle complete! *{user}* has finished all jobs! :star:",
            f"All of *{user}*’s jobs have crossed the finish line! :checkered_flag:",
            f"ROSA says goodbye to *{user}*’s jobs. Until next time! :wave:",
            f"No more crunching numbers for *{user}*! Jobs are done! :bar_chart:",
            f"All of *{user}*’s computations are history! :scroll:",
            f"Ding! *{user}*’s job queue is empty now! :bell:",
            f"Nothing left in the ROSA queue for *{user}*! :ghost:",
            f"Job execution complete! *{user}*’s tasks are finished! :white_check_mark:",
            f"Well done, *{user}*! All your ROSA jobs are complete. :sports_medal:",
            f"ROSA is free from *{user}*'s jobs! :bird:"
        ]

        if event == "new":
            return random.choice(new_job_messages)
        elif event == "finished":
            return random.choice(finished_job_messages)
        else:
            raise ValueError("Invalid event type. Use 'new' or 'finished'.")


    def get_slurm_queue(self):
        """Fetch the current slurm queue status using squeue."""

        try:
            result = subprocess.run(["squeue", "-A", self.group_id, "-o", "%11i %35j %20u %5C %13m %8T %10M %9l %6D %R"],
                                    capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Error fetching slurm queue: {e}"


    def get_known_user_name(self, user):
        """Replaces ROSA user ID with known user ID when applicable"""

        return self.known_users[user] if user in self.known_users else user


    def get_current_users(self, slurm_queue):
        """Extracts a set of unique users from the Slurm queue output."""

        lines = slurm_queue.strip().split('\n')[1:]

        users = set([self.get_known_user_name(u) for u in [re.split(r'\s+', line, maxsplit=9)[2] for line in lines]])

        return users


    def check_user_changes(self, slurm_queue=None):
        """Check for new and finished users and send Slack notifications."""

        if not slurm_queue:
            slurm_queue = self.get_slurm_queue()

        current_users = self.get_current_users(slurm_queue)

        # find out hat has changed
        new_users = current_users - self.previous_users
        finished_users = self.previous_users - current_users

        for user in new_users:
            self.message(self.get_random_slack_notification_for_jobs(user, 'new'))

        for user in finished_users:
            self.message(self.get_random_slack_notification_for_jobs(user, 'finished'))

        self.previous_users = current_users


    def summarize_jobs(self, slurm_queue=None):
        """Summarizes job statistics per user based on the provided job output."""

        if not slurm_queue:
            slurm_queue = self.get_slurm_queue()

        lines = slurm_queue.strip().split('\n')

        job_data = []
        for line in lines[1:]:
            parts = re.split(r'\s+', line, maxsplit=9)
            job_data.append({
                'JOBID': parts[0],
                'NAME': parts[1],
                'USER': parts[2],
                'CPUS': int(parts[3]),
                'STATE': parts[5],
                'TIME': self.parse_time(parts[6]),
            })

        user_jobs = defaultdict(list)
        for job in job_data:
            user_jobs[job['USER']].append(job)

        summaries = []
        for user, jobs in user_jobs.items():
            user = self.get_known_user_name(user)
            total_jobs = len(jobs)
            total_cpus = sum(job['CPUS'] for job in jobs)
            longest_job = max(jobs, key=lambda x: x['TIME'])
            most_recent_job = min(jobs, key=lambda x: x['TIME'])

            if total_jobs == 1:
                summary = (f"> *{user}* has a single job, _{longest_job['NAME']}_, that is using a total of *{total_cpus}* "
                           f"{'CPUs' if total_cpus > 1 else 'CPU'} and has been running for *{longest_job['TIME']}*.")
            else:
                summary = (f"> *{user}* has *{total_jobs}* jobs using a total of *{total_cpus}* CPUs. "
                           f"The longest job,  _{longest_job['NAME']}_ has been running for *{longest_job['TIME']}* "
                           f"and their most recently started job is _{most_recent_job['NAME']}_.")

            summaries.append(summary)

        jobs_summary = '\n\n'.join(summaries)

        if len(jobs_summary):
            message = f"""A *status update* from ROSA (by <@rosalind> on head node _{platform.node()}_ at *{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*)\n\n{jobs_summary}"""
            self.message(message)


    def message(self, message):
        """Send a message to Slack using the webhook (or print it to the terminal)"""

        print('--- Slack Message ---')
        print(message)
        print()

        if self.webhook and not self.stdout_only:
            payload = {"text": message}
            response = requests.post(self.webhook, json=payload)
            return response.status_code, response.text
        else:
            return None, None


    def __test_run(self):
        for slurm_output_path in glob.glob('sandbox/slurm-outputs-for-testing/*.txt'):
            print(f'#' * (len(slurm_output_path) + 8))
            print(f'### {slurm_output_path} ###')
            print(f'#' * (len(slurm_output_path) + 8))
            print()
            slurm_queue = open(slurm_output_path).read()
            self.check_user_changes(slurm_queue)
            self.summarize_jobs(slurm_queue)
            time.sleep(1)


    def __actual_run(self):
        output = self.get_slurm_queue()
        self.previous_users = self.get_current_users(output)

        while True:

            if int(time.time()) % self.user_jobs_interval < 60:
                # runs every minute
                self.check_user_changes()

            if int(time.time()) % self.overall_summary_interval < 60:
                # runs every 6 hour-cycle
                self.summarize_jobs()

            time.sleep(self.check_interval)


    def run(self):
        """Main loop to check the Slurm queue and send updates to Slack."""

        if self.testing:
            self.__test_run()
        else:
            self.__actual_run()


def get_user_args():
    """Parses commandline arguments"""

    parser = argparse.ArgumentParser()
    groupA = parser.add_argument_group('ESSENTIALS', 'Essential information related to Slurm and Slack')
    groupA.add_argument('--partition', metavar="ID", default=None, help="Your group ID or partition on Slurm. If you "
        "have one, you can leave this empty and see what happens (we haven't really tested it lol).")
    groupA.add_argument('--webhook', metavar="URL", default=None, help="Slack web hook for the program to "
        "communicate with you.")

    groupB = parser.add_argument_group('INTERVALS', 'Defaults are just fine, but you can also set anyting you want here')
    groupB.add_argument('--squeue-check-interval', metavar="SECONDS", default=60, type=int, help="The frequency of "
        "squeue output collection. The default of 60, which means rosalind will check the slurm output once every minute. "
        "It is a very bad idea to change this :/")
    groupB.add_argument('--overall-summary-interval', metavar="SECONDS", default=21600, type=int, help="The frequency of "
        "overall job summaries to be prepared and sent to Slack. The default is 21600, i.e., every 6 hour cycle.")
    groupB.add_argument('--user-jobs-interval', metavar="SECONDS", default=60, type=int, help="The frequency of "
        "checking changes in user jobs (new jobs, finished jobs, etc). The default is 60, i.e., every minute.")


    groupC = parser.add_argument_group('DEVELOPMENT & TESTING', 'Parameters to test the program.')
    groupC.add_argument('--stdout-only', action="store_true", default=False, help="Don't send anything to Slack, "
        "print messages that were meant to be sent to slack to the terminal.")
    groupC.add_argument('--testing', action="store_true", default=False, help="Declaring this flag will instruct the "
        "program to 'simulate' a bunch of slurm outputs, and will set all the intervals the way it sees fit. The "
        "messages that were meant to be sent to the Slack environment will also not be sent to the slack environment, "
        "but printed on screen just so you can see things.")

    return parser.parse_args()



if __name__ == "__main__":
    monitor = SlurmMonitor(get_user_args())
    monitor.run()
