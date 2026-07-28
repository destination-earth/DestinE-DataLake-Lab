# Print example function for the dedl module. 
# This function can be used in any task that has access to the dedl module.
# It could also be used in a KubernetesPodOperator by creating a custom image that copies over the dedl module to the image.
# Then scripts running in the KubernetesPodOperator could import the dedl module and call this function to print out a message.

def demo_print():
    print("This is a print tool function from the dedl module.")