import logging
import arrow
import datetime
import yaml
import sys, os
import platomic_api_client as pac
import properties as properties

# Initialize logging
def init_logging(current_date):
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)

    logs_folder = 'logs'
    try:
        os.mkdir(logs_folder)  
    except Exception as e:
        # This exception happends when the folder already exists.
        pass
    
    fileHandler = logging.FileHandler("{0}/{1}.log".format('logs', f"script_log_{current_date.strftime('%m-%d-%Y_%H-%M-%S')}"))
    
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

def retrieve_court_availability(resources, target_date, tenant_id):
    logging.info(f"      Retrieving Availability")
    start_min = target_date.strftime('%Y-%m-%dT00:00:00')
    start_max = target_date.strftime('%Y-%m-%dT23:59:59')
    availability = pac.get_tenant_availability(tenant_id=tenant_id, start_min=start_min, start_max=start_max)
    for court in availability:
        num_court = None
        for num in resources:
            if resources[num]['resource_id'] == court['resource_id']:
                num_court = num
                break
        resources[num_court]['slots'] = court['slots']
        resources[num_court]['slots'] = list(resources[num_court]['slots'])
        
def check_if_target_day_already_booked(target_date):
    with open('booked_days.yml', 'r') as file:
        yaml_file = yaml.safe_load(file)
        try:
            if yaml_file is None:
                return False
            else:
                return target_date in yaml_file 
        except:
            return False
        
def add_current_date_to_booked(target_date):
    with open('booked_days.yml','r') as yamlfile:
        cur_yaml = yaml.safe_load(yamlfile) # Note the safe_load
        if cur_yaml is None:
            cur_yaml = dict()
        cur_yaml[target_date] = True

    if cur_yaml:
        with open('booked_days.yml','w') as yamlfile:
            yaml.safe_dump(cur_yaml, yamlfile) # Also note the safe_dump

def calculate_if_valid_day_of_week(target_date):
    days_of_week = dict()
    days_of_week[0] = 'MONDAY'
    days_of_week[1] = 'TUESDAY'
    days_of_week[2] = 'WEDNESDAY'
    days_of_week[3] = 'THURSDAY'
    days_of_week[4] = 'FRIDAY'
    days_of_week[5] = 'SATURDAY'
    days_of_week[6] = 'SUNDAY'
    logging.info(f"Target Booking is: {days_of_week[target_date.datetime.weekday()]}: {target_date.strftime('%m-%d-%Y')}")
    return target_date.datetime.weekday() in [0,2,3,4]

def book_target_day(target_date, club_id):
        
    club = pac.get_tenant(tenant_id=club_id)
    logging.info(f"   Retrieved Data of Club: {club['tenant_name']}")
    
    resources = dict()
    for resource in  club['resources']:
        num_court = resource['name'].lower().strip().split(' ')[1]
        resources[num_court] = dict()
        resources[num_court]['name'] = resource['name'].lower().strip()
        resources[num_court]['resource_id'] = resource['resource_id']
        logging.info(f"         Court: {resources[num_court]['name']} -> {resources[num_court]['resource_id']}")
        
        
    retrieve_court_availability(resources=resources, target_date=target_date, tenant_id=club_id)
    
    court_booked = False

    for time in ['17:00:00', '17:30:00', '18:00:00', '18:30:00', '19:00:00']:
        if court_booked:
            break

        for num_court in [4,1,2,3,5,7,6]:
            if court_booked:
                break

            num_court = str(num_court)
            if num_court in resources.keys():
                resource = resources[num_court]
                
                if 'slots' in resources[num_court].keys():
                    for slot in resources[num_court]['slots']:
                        if court_booked:
                            break

                        if slot['duration'] == 90 and slot['start_time'] == time:
                            start = f"{target_date.strftime('%Y-%m-%dT')}{slot['start_time']}"
                            logging.info(f"      Duration is 90 minutes and within optimal time range: {start}. Booking court {resources[num_court]['name']}......")
                        
                            if pac.book_court(resource_id=resources[num_court]['resource_id'], tenant_id=club_id, start=start) is not None:
                                court_booked = True
                                add_current_date_to_booked(target_date=target_date.strftime('%m-%d-%Y'))
                                logging.info(f"     >>>>>>>>>> Court Booked: {slot['start_time']} <<<<<<<<<<< ")
            
    if not court_booked:
        logging.info(f"         There wasn't any available slot to be booked the {target_date.strftime('%m-%d-%Y')} at 18, 18.30, 19, 19.30, 20")

    return court_booked
        
    
                
        
if __name__ == "__main__":
    current_date=arrow.now()
    init_logging(current_date=current_date)
    
    for index in range(5, 0, -1):

        logging.info(f"________________________________________________________________________________")
        target_date = arrow.now().shift(days=index)
        if calculate_if_valid_day_of_week(target_date=target_date):
            if not check_if_target_day_already_booked(target_date=target_date.strftime('%m-%d-%Y')):
                if not book_target_day(target_date=target_date, club_id=properties.get_property('tenant_id_central')):
                    book_target_day(target_date=target_date, club_id=properties.get_property('tenant_id_alday'))
            else:
                logging.info(f"______Current day is listed as already booked: {target_date.strftime('%m-%d-%Y')}______")
        else:
            logging.info(f"   Canceling Booking since it's not an allowed Day. Only Allowed [MONDAY, WEDNESDAY, THURSDAY, FRIDAY]")