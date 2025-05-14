# Build an Application That Can “See” and “Understand” Visual Data.

[![License: UPL](https://img.shields.io/badge/license-UPL-green)](https://img.shields.io/badge/license-UPL-green) [![Quality gate](https://sonarcloud.io/api/project_badges/quality_gate?project=oracle-devrel_test)](https://sonarcloud.io/dashboard?id=oracle-devrel_test)



## Introduction
Oracle JET uses the Virtual DOM (VDOM) architecture and integrates OCI Vision services for enhanced functionality. The Oracle JET VDOM UI application consumes responses from the OCI Vision service. This code is for Oracle JET applications based on the Virtual DOM architecture. This project is developed for use with the Oracle JavaScript Extension Toolkit (JET) coding environment.


## Getting Started

There are three parts of the application. The code for part 3 is in this repository.

• Part 1: Upload  images to OCI bucket.

1.	Login to your Oracle Cloud Account. If you don't have one yet, sign up at cloud.oracle.com.
2.	Create a compartment from the OCI “Identity and Security” menu and note the CompartmentID.
3.	From the Storage menu, choose the “Bucket” option. Create a bucket the compartment you created above and name it “ORACLE_DEMO_BUCKET” .
4.	Upload sample images.
5.	Set up an API signing key and OCI profile mentioned in  OCI documentation.

![OCI bucket](https://github.com/user-attachments/assets/d9e29dce-2088-4dc3-9b20-c3b65c0f74e5)

    
• Part 2: Integration of OCI Java SDK with OCI Vision service to handle image processing within a Spring Boot application. 

  •	Clone the repository below and follow its instructions mentioned in part 2 section of [oracle-jet-vdom-and-oci-vision](https://blogs.oracle.com/developers/post/oracle-jet-vdom-and-oci-vision)  to run the code locally.
  
[oci-sdk-java-samples](https://github.com/user-attachments/assets/c12954b7-56b5-4c86-b680-2625364ed1fb)


• Part 3: Developing an Oracle JET (VDOM) application to consume and display the results from OCI Vision Service.
	Clone the repository below and execute the command below in the local terminal.
    
        
                    npx ojet serve
**The final application should look as follows on a localhost server:**
Our blog will feature a one-page application with Object Storage Details and OCI Vision Result sections. In the Object Storage Details section, users enter Tenancy Region and Bucket Name. After validating the inputs, the application fetches the images stored in the provided object storage, which are then displayed in object lists. Upon submission, the OCI Vision API analyzes the selected image, displaying both the object and text in the OCI Vision Result section.

![OJET VDOM application](https://github.com/user-attachments/assets/c12954b7-56b5-4c86-b680-2625364ed1fb)


Note: image courtesy of pixabay.com

### Prerequisites


•	Nodejs

•	Java 17

•	Integrated Development Environment (IDE)

•	Oracle Cloud Account (free oracle cloud services should be sufficient)



## Contributors
Author: Kulraj Singh Chouhan
Collaborators: NA
Last Review: Sept 2024

## References
[oracle-jet-vdom-and-oci-vision](https://blogs.oracle.com/developers/post/oracle-jet-vdom-and-oci-vision)

[OCI Vision ](https://docs.oracle.com/en/solutions/ai-vision-extract-data/index.html#GUID-FA774176-6223-4E78-89D0-887BB6BCA4E4)

## Contributing
<!-- If your project has specific contribution requirements, update the
    CONTRIBUTING.md file to ensure those requirements are clearly explained. -->

This project welcomes contributions from the community. Before submitting a pull
request, please [review our contribution guide](./CONTRIBUTING.md).

## Security

Please consult the [security guide](./SECURITY.md) for our responsible security
vulnerability disclosure process.

## License
Copyright (c) 2024 Oracle and/or its affiliates.

Licensed under the Universal Permissive License (UPL), Version 1.0.

See [LICENSE](LICENSE.txt) for more details.

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE.  FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK. 
