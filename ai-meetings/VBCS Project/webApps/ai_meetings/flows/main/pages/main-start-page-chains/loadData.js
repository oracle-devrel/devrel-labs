define([
  'vb/action/actionChain',
  'vb/action/actions',
  'vb/action/actionUtils',
], (
  ActionChain,
  Actions,
  ActionUtils
) => {
  'use strict';

  class loadData extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      if ($page.variables.meetingID >0 ||  $page.variables.parURL) {
      

      $page.variables.loading = true;
        $page.variables.uploadSuccess = true;
        $page.variables.meetingCreated = true;

      await Actions.callChain(context, {
        chain: 'loadMeeting',
      });

        if (!($page.variables.transcriptionID >0)) {
          await Actions.fireNotificationEvent(context, {
            summary: 'Attention',
            message: 'You are trying to access a meeting that doesn\'t exist.',
            displayMode: 'transient',
            type: 'error',
          });

          const navigateToPageMainBrowseResult = await Actions.navigateToPage(context, {
            page: 'main-browse',
          });
        }

      const callRestBusinessObjectsGetTranscriptionsResult = await Actions.callRest(context, {
        endpoint: 'businessObjects/get_Transcriptions',
        uriParams: {
          'Transcriptions_Id': $page.variables.transcriptionID,
        },
      });

      $page.variables.jobId = callRestBusinessObjectsGetTranscriptionsResult.body.jobID;

      const callRestCreateJobGetTranscriptionJobsResult = await Actions.callRest(context, {
        endpoint: 'CreateJob/getTranscriptionJobs',
        uriParams: {
          transcriptionJobId: $page.variables.jobId,
        },
      });

      $page.variables.jobStatus = callRestCreateJobGetTranscriptionJobsResult.body.lifecycleState;
      $page.variables.jobCompletion = callRestCreateJobGetTranscriptionJobsResult.body.percentComplete;
      $page.variables.outputlocation = callRestCreateJobGetTranscriptionJobsResult.body.outputLocation.prefix;


      if (callRestBusinessObjectsGetTranscriptionsResult.body.status!==callRestCreateJobGetTranscriptionJobsResult.body.lifecycleState) {
        const callRestBusinessObjectsUpdateTranscriptionsResult = await Actions.callRest(context, {
          endpoint: 'businessObjects/update_Transcriptions',
          uriParams: {
            'Transcriptions_Id': $page.variables.transcriptionID,
          },
          body: {
                    "status":  $page.variables.jobStatus,
                   // "speakersN": 1
                },
        });
      }

      if (callRestCreateJobGetTranscriptionJobsResult.body.lifecycleState==='SUCCEEDED') {

        const currentDate = new Date();
        // Add 3 hours to the current time
        currentDate.setHours(currentDate.getHours() + 3);
        // Convert the date to RFC 3339 format
        const rfc3339Date = currentDate.toISOString();
        // Remove the milliseconds and 'Z' at the end, then append the timezone offset
        const expirationTime = rfc3339Date.split('.')[0] + currentDate.toISOString().slice(19);

        let urlTemp = $page.variables.outputlocation +'wedoinfra_AI_Meetings_'+ callRestCreateJobGetTranscriptionJobsResult.body.inputLocation.objectLocations[0].objectNames[0]+'.json';
        const callRestStorageCreatePARResult = await Actions.callRest(context, {
          endpoint: 'Storage/createPAR',
          uriParams: {
            bucketName: $application.variables.bucketName,
            namespaceName: $application.variables.namespace,
          },
          body: {
            accessType: 'ObjectRead',
            name: 'PARTest',
            objectName: urlTemp,
            timeExpires: expirationTime,
          },
        });

          $page.variables.spareTime = false;

        $page.variables.parURL = callRestStorageCreatePARResult.body.fullPath;
        let tokens=[];


          async function procesarTranscripciones() {
              try {
                        // Get the JSON from the URL
                        const respuesta = await fetch($page.variables.parURL);
                        const datos = await respuesta.json();
                        // Check if the JSON is in the expected format
                        if (!datos.transcriptions || !Array.isArray(datos.transcriptions)) {
                            console.error('The JSON is not in the expected format.');
                            return;
                        }
                        const conversation = datos.transcriptions[0].transcription;
                         $page.variables.transcriptionText = conversation;
                        
                  
                        
                        
                        const speakers = datos.transcriptions[0].speakerCount;       
                        $page.variables.nParticipants = speakers; 
                        const callRestBusinessObjectsUpdateTranscriptionsResult = await Actions.callRest(context, {
                            endpoint: 'businessObjects/update_Meetings',
                            uriParams: {
                                'Meetings_Id': $page.variables.meetingID,
                            },
                            body: {
                                "speakersN": Number(speakers),
                            },
                        });
                        
                        // Initialise an object to separate tokens by speaker
                        const tokensBySpeaker = {};
                        for (let i = 0; i < speakers; i++) {
                            tokensBySpeaker[`Speaker${i}`] = [];
                        }
                        
                        // Asumiendo que solo estamos interesados en la primera transcripción
                        
                       tokens = datos.transcriptions[0].tokens;
                   
                   
                   // Obtener la longitud del array de tokens
                 // const numTokens = datos.transcriptions[0].tokens.length;

                  // Crear un array con índices desde 0 hasta numTokens - 1
               //   $page.variables.tokens = Array.from({ length: numTokens }, (v, k) => k);
                       
                      //  console.log("token: "+JSON.stringify(tokens));
                        if (!tokens) {
                            console.error('No tokens were found in the transcription');
                            return;
                        }
                        
                        // Iterate through tokens and sort them out
                        for (const token of tokens) {
                            if (tokensBySpeaker.hasOwnProperty(`Speaker${token.speakerIndex}`)) {
                              //  $page.variables.tokenArray.push({"token":token.token,"speakerIndex":token.speakerIndex});
                                tokensBySpeaker[`Speaker${token.speakerIndex}`].push(token.token);
                            } /*else {
                                console.error(`Speaker rate unknown: ${token.speakerIndex}`);
                            }*/
                        }
                        
                        
                        // Print the results
                        for (let i = 0; i < speakers; i++) {
                            console.log(`Tokens Speaker ${i}:`, tokensBySpeaker[`Speaker${i}`].join(' '));
                        }
                    
                        return;
                      
                } catch (error) {
                  // Error handling (e.g. network or parse problem)
                  console.error('Error getting or processing JSON:', error);
                  return false;
                      }
            }
          
            let result = await procesarTranscripciones();

            let groupWords = await agruparPorSpeaker(tokens);
         //   alert(JSON.stringify(groupWords));
            $page.variables.tokenArray=groupWords;
        $page.variables.transcriptionTask = true;

            function agruparPorSpeaker(tokens) {
                  const agrupados = [];
                  let currentSpeaker = null;
                  let currentText = "";

                  tokens.forEach(token => {
                      if (token.speakerIndex !== currentSpeaker) {
                          if (currentSpeaker !== null) {
                              agrupados.push({
                                  speakerIndex: currentSpeaker,
                                  token: currentText.trim()
                              });
                          }
                          currentSpeaker = token.speakerIndex;
                          currentText = token.token;
                      } else {
                          currentText += " " + token.token;
                      }
                  });

                  if (currentSpeaker !== null) {
                      agrupados.push({
                          speakerIndex: currentSpeaker,
                          token: currentText.trim()
                      });
                  }

                  return agrupados;
              }

         await Actions.callChain(context, {
        chain: 'sentimentDetection',
      });

      await Actions.callChain(context, {
        chain: 'summarization',
      });

          await Actions.callChain(context, {
            chain: 'ActionPeopleMentions',
          });

      $page.variables.loading=false;
        
      } else if (callRestCreateJobGetTranscriptionJobsResult.body.lifecycleState==='IN_PROGRESS') {
          $page.variables.loading = true;
          $page.variables.spareTime = true;

      }
    
    

    }
    }
  }

  return loadData;
});
