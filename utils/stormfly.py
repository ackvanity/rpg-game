# TODO: Schema validator for story entities

import gobber

# def 

def fetch_key(entity: gobber.EntityID, keys: list[str]):
  dct = gobber.get_entity_data(entity.get_file())
  for key in keys:
    if key not in dct:
      return None
    dct = dct[key]
  
  return dct

def validate(entity: gobber.EntityID):
  if entity[0] == "character":
    pass