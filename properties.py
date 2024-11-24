import yaml


#Returns the property value based on the name provided
def get_property(name):
    with open('properties.yml', 'r') as file:
        yaml_file = yaml.safe_load(file)
        try:
            return yaml_file[name]
        except Exception:
            return None
    