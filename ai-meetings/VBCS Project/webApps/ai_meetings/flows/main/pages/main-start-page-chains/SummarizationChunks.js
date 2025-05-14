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

  class SummarizationChunks extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;
      
      
      async function splitText(text, chunkSize) {
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
      
          async function summarizeText(text) {
          //  alert("Texto total: " + text);
      const chunkSize = 3500; // Example chunk size
      const chunks = await splitText(text, chunkSize);
      
      const summaries = await Promise.all(chunks.map(async chunk => {
          //   alert("Procesando " + chunk);
        return await summarizeChunk(chunk);
      }));
      
         //   alert("Resúmenes intermedios: " + summaries);
      const combinedSummary = summaries.join(' ');
      return combinedSummary;
          }
      
          async function summarizeChunk(text) {
      const callRestSummarizationPostSummarizeTextResult = await Actions.callRest(context, {
        endpoint: 'Summarization/postSummarizeText',
        body: {
          "compartmentId": $application.variables.compartment_id,
       //     "additionalCommand":"Generate a summary",
          "extractiveness": $page.variables.extractiveness,
          "format": $page.variables.format,
          "input": text,
          "length": $page.variables.length,
          "servingMode": {
            "modelId": "cohere.command",
            "servingType": "ON_DEMAND"
          },
          "temperature": 0.0
        },
      });
      return callRestSummarizationPostSummarizeTextResult.body.summary;
          }
      
          async function startSummarization() {
      const text = $page.variables.transcriptionText; // Ensure this is properly initialized and accessible
      let result = await summarizeText(text);
      
           // let result2 = await summarizeText2(result, context);
      console.log("Result: " + result);
       $page.variables.summaryText=result;
          }



      const size = $page.variables.transcriptionText.length;
    if (size < 250) {
          $page.variables.minimumSize = true;
          $page.variables.summaryStatus = true;
          return;
    }

   // alert(size);
    if (size < 3500) {
            $page.variables.loading = true;
              const callRestSummarizationPostSummarizeTextResult3 = await Actions.callRest(context, {
            endpoint: 'Summarization/postSummarizeText',
            body: {
              "compartmentId": $application.variables.compartment_id,
              "extractiveness": $page.variables.extractiveness,
              "format": $page.variables.format,
              "input": $page.variables.transcriptionText,
              "length": $page.variables.length,
              "servingMode": {
                "modelId": "cohere.command",
                "servingType": "ON_DEMAND"
              },
              "temperature": 0.0
            },
          });
          $page.variables.summaryText=callRestSummarizationPostSummarizeTextResult3.body.summary;
            $page.variables.loading = false;
            $page.variables.summaryStatus = true;
            return;
      }else{
          $page.variables.loading = true;
          await startSummarization(context);
          const callRestSummarizationPostSummarizeTextResult2 = await Actions.callRest(context, {
            endpoint: 'Summarization/postSummarizeText',
            body: {
                "compartmentId": $application.variables.compartment_id,
        //        "additionalCommand":"Maximum 10 main points",
                "extractiveness": $page.variables.extractiveness,
                "format": $page.variables.format,
                "input": $page.variables.summaryText,
                "length": $page.variables.length,
                "servingMode": {
                  "modelId": "cohere.command",
                  "servingType": "ON_DEMAND"
                },
                "temperature": 0.0
              },
              });
            $page.variables.summaryText=callRestSummarizationPostSummarizeTextResult2.body.summary;
            $page.variables.loading = false;
            $page.variables.summaryStatus = true;
            return;
      }




  }
  }
  return SummarizationChunks;
  
});
