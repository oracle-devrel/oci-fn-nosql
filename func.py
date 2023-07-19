import io
import json
import logging
import oci
import os

from fdk import response

# Retrieve the values from environment variables
tenancy_ocid = os.environ.get("OCI_TENANCY_OCID")
user_ocid = os.environ.get("OCI_USER_OCID")
fingerprint = os.environ.get("OCI_FINGERPRINT")
private_key_file_location = os.environ.get("OCI_PRIVATE_KEY_FILE")
region = os.environ.get("OCI_REGION")

compartment_ocid = os.environ.get("OCI_COMPARTMENT_OCID")

# Set up the configuration
config = {
    "user": user_ocid,
    "key_file": private_key_file_location,
    "fingerprint": fingerprint,
    "tenancy": tenancy_ocid,
    "region": region
}

def handler(ctx, data: io.BytesIO = None):
    
    try:
        body = json.loads(data.getvalue())
        bucket_name  = body["data"]["additionalDetails"]["bucketName"]
        object_name  = body["data"]["resourceName"]
        logging.getLogger().info('Function invoked for bucket upload: ' + bucket_name)
    except (Exception, ValueError) as ex:
        logging.getLogger().info('error parsing json payload: ' + str(ex))
    

    # Get the object data from Object Storage
    obj = get_object(bucket_name, object_name)

    logging.getLogger().info('JSON File Object: ' + str(obj))
    # Convert the object data to a Python dictionary
    person_data = json.loads(obj.decode("utf-8"))
    logging.getLogger().info('person_data: ' + str(person_data))   

    # Get the NoSQL client
    nosql_client = oci.nosql.NosqlClient(config)

    # Write the person data to the NoSQL table
    table_name = "person"
    record = {
        "id": person_data["id"],
        "name": person_data["name"],
        "age": person_data["age"],
        "gender": person_data["gender"]
    }

    # Update the target nosql table with the data read from the file
    update_row_response = nosql_client.update_row(
        table_name_or_id="person",
        update_row_details=oci.nosql.models.UpdateRowDetails(
            value=record,
            compartment_id=compartment_ocid,
            option="IF_ABSENT",
            is_get_return_row=False,
            timeout_in_ms=500,
            is_ttl_use_table_default=True,
            is_exact_match=False)
        )
    # Get the data from response
    print(update_row_response.data)

    # Return a success status
    return {
        "status": 200,
        "message": "Person data successfully written to NoSQL table"
    }

def get_object(bucketName, objectName):
    signer = oci.auth.signers.get_resource_principals_signer()
    client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
    namespace = client.get_namespace().data
    try:
        print("Searching for bucket and object", flush=True)
        object = client.get_object(namespace, bucketName, objectName)
        print("found object", flush=True)
        if object.status == 200:
            print("Success: The object " + objectName + " was retrieved with the content: ", flush=True)
        else:
            print("Failed: The object " + objectName + " could not be retrieved.")
    except Exception as e:
        print("Failed: " + str(e.message))
    return object.data.content