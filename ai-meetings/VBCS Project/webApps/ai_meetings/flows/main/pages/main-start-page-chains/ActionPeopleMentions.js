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

  class ActionPeopleMentions extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;


  async function startMentioning() {
      const text = $page.variables.transcriptionText; // Ensure this is properly initialized and accessible
      let result = await analyzeText(text);

      console.log("Result: " + result);
    //   $page.variables.summaryText=result;
    }
    await startMentioning();
    $page.variables.languageProcessingFinish=true;
    $page.variables.loading =false;

    async function splitText(text, chunkSize) {
   //   alert(text + " " + chunkSize);
      const chunks = [];
      let startIndex = 0;

      while (startIndex < text.length) {
        let endIndex = startIndex + chunkSize;

        if (endIndex > text.length) {
          endIndex = text.length;
        } else {
          while (endIndex > startIndex && text[endIndex] !== ' ') {
            endIndex--;
          }

          if (endIndex === startIndex) {
            endIndex = Math.min(startIndex + chunkSize, text.length);
          }
        }

        const chunk = text.slice(startIndex, endIndex).trim();
        chunks.push(chunk);
        startIndex = endIndex + 1;
      }

      return chunks;
    }


    async function analyzeText(text) {
      const chunkSize = 3500; // Example chunk size
      const chunks = await splitText(text, chunkSize);

      const analysis = await Promise.all(chunks.map(async chunk => {
      // alert("Procesando " + chunk);
        return mentionAnalysis(chunk);
      }));
     // const combinedSummary = analysis.join(' ');
      return; // combinedSummary;
    }
    
  
  function processEntities(data) {   
    try{ 
        data.documents[0].entities.forEach(entity => {
            if ((entity.type === "PERSON") && (entity.score>0.7)) {
                $page.variables.arrayMention.push(entity.text);
            } else if ((entity.type === "ORGANIZATION") && (entity.score>0.8)) {
                $page.variables.arrayOrg.push(entity.text);
            } else if ((entity.type === "PRODUCT") && (entity.score>0.8)) {
                $page.variables.arrayProduct.push(entity.text);
            } else if ((entity.type === "DATETIME") && (entity.score>0.8)) {
                $page.variables.arrayDatetime.push(entity.text);
            }else if ((entity.type === "LOCATION") && (entity.score>0.8)) {
                $page.variables.arrayLocation.push(entity.text);
            }
        })
 } catch (error) {
      console.error(error);
 }

// Elimina duplicados usando Set
    $page.variables.arrayMention = [...new Set($page.variables.arrayMention)];
    $page.variables.arrayOrg = [...new Set($page.variables.arrayOrg)];
     $page.variables.arrayProduct = [...new Set($page.variables.arrayProduct)];
    $page.variables.arrayLocation = [...new Set($page.variables.arrayLocation)];
     $page.variables.arrayDatetime = [...new Set($page.variables.arrayDatetime)];
    
    let json = {"personEntities": $page.variables.arrayMention, "orgEntities": $page.variables.arrayOrg};
//alert(JSON.stringify(json));
    return json; // Retorna el objeto JSON directamente
}



    async function mentionAnalysis(text) {
       const callRestSentimentAnalysisDetectLanguageEntitiesResult = await Actions.callRest(context, {
        endpoint: 'SentimentAnalysis/DetectLanguageEntities',
        body: {
          "documents": [
      {             "key": "doc1", "text": text
               }
          ]
      },
      });
      const callFunctionResult = processEntities(callRestSentimentAnalysisDetectLanguageEntitiesResult.body);
      return true;
    
    }

      return;
    }
  }
  
  return ActionPeopleMentions;
});
