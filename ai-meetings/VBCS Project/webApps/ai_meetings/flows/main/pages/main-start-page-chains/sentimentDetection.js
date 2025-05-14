/*define([
  'vb/action/actionChain',
  'vb/action/actions',
  'vb/action/actionUtils',
], (
  ActionChain,
  Actions,
  ActionUtils
) => {

  'use strict';

  class sentimentDetection extends ActionChain {*/
    /**
     * @param {Object} context
     */
  /*  async run(context) {
      const { $page, $flow, $application } = context;


      

      const callRestSentimentAnalysisPostBatchDetectLanguageSentimentsResult = await Actions.callRest(context, {
        endpoint: 'SentimentAnalysis/postBatchDetectLanguageSentiments',
        body: {
          documents: [
            {
              key: 'doc1',
              text: $page.variables.transcriptionText.substr(0, 4999),
            },
          ],
        },
        uriParams: {
          level: 'SENTENCE',
        },
      });

      if (callRestSentimentAnalysisPostBatchDetectLanguageSentimentsResult.status===200) {
        try {
          $page.variables.meetingSentiment = callRestSentimentAnalysisPostBatchDetectLanguageSentimentsResult.body.documents[0].documentSentiment;
          $page.variables.positive = callRestSentimentAnalysisPostBatchDetectLanguageSentimentsResult.body.documents[0].documentScores.Positive;
          $page.variables.negative = callRestSentimentAnalysisPostBatchDetectLanguageSentimentsResult.body.documents[0].documentScores.Negative;
          $page.variables.neutral = callRestSentimentAnalysisPostBatchDetectLanguageSentimentsResult.body.documents[0].documentScores.Neutral;
          $page.variables.mixed = callRestSentimentAnalysisPostBatchDetectLanguageSentimentsResult.body.documents[0].documentScores.Mixed;
          $page.variables.chartDataArray[0].value = $page.variables.positive;
          $page.variables.chartDataArray[1].value = $page.variables.negative;
          $page.variables.chartDataArray[2].value = $page.variables.neutral;
          $page.variables.chartDataArray[3].value = $page.variables.mixed;

          let data = callRestSentimentAnalysisPostBatchDetectLanguageSentimentsResult.body.documents[0].sentences;
        // alert("original data: "+JSON.stringify(data));
            const result = data.map(item => {
                const scores = item.scores;
                const highestScore = Object.keys(scores).reduce((a, b) => scores[a] > scores[b] ? a : b);
                return {
                    sentence: item.text,
                    sentiment: item.sentiment,
                    value: (scores[highestScore] * 100).toFixed(2) // Convertir a porcentaje y redondear a dos decimales
                };
            });
        //   alert(JSON.stringify(result));
        $page.variables.tableArray= result;
        } catch (error) {

          await Actions.fireNotificationEvent(context, {
            summary: 'Attention',
            message: 'There was an error getting the sentiment',
            displayMode: 'transient',
            type: 'warning',
          });
          
        }

       
      }

      

      return;


    }
  }

  return sentimentDetection;
});
*/


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

  class sentimentDetection extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;
      
      $page.variables.loading = true;
      await processSentimentAnalysis();
      $page.variables.loading = false;
    

    async function processSentimentAnalysis() {
      const text = $page.variables.transcriptionText;
      const chunkSize = 4999; // Adjust based on API limits
      const chunks = splitText(text, chunkSize);

      const sentimentResults = await Promise.all(chunks.map(async (chunk, index) => {
        return callSentimentAnalysisAPI(chunk, index);
      }));

      compileSentimentResults(sentimentResults);
    }

    function splitText(text, chunkSize) {
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

    async function callSentimentAnalysisAPI(text, index) {
      return Actions.callRest(context, {
        endpoint: 'SentimentAnalysis/postBatchDetectLanguageSentiments',
        body: {
          documents: [
            {
              key: `doc${index}`,
              text: text,
            },
          ],
        },
        uriParams: {
          level: 'SENTENCE',
        },
      });
    }


function compileSentimentResults(results) {
  let allSentiments = [];
  let totalPositive = 0;
  let totalNegative = 0;
  let totalNeutral = 0;
  let totalMixed = 0;
  let count = 0;

  results.forEach(result => {
    if (result.status === 200) {
      try {
        const documentSentiment = result.body.documents[0].documentSentiment;
        const scores = result.body.documents[0].documentScores;

        totalPositive += scores.Positive;
        totalNegative += scores.Negative;
        totalNeutral += scores.Neutral;
        totalMixed += scores.Mixed;
        count++;

        const data = result.body.documents[0].sentences;
        const processedData = data.map(item => {
          const scores = item.scores;
          const highestScore = Object.keys(scores).reduce((a, b) => scores[a] > scores[b] ? a : b);
          return {
            sentence: item.text,
            sentiment: item.sentiment,
            value: (scores[highestScore] * 100).toFixed(2) // Convert to percentage and round to two decimals
          };
        });
        allSentiments = allSentiments.concat(processedData);
      } catch (error) {
        Actions.fireNotificationEvent(context, {
          summary: 'Attention',
          message: 'There was an error processing the sentiment data',
          displayMode: 'transient',
          type: 'warning',
        });
      }
    }
  });

  // Calculate averages
  if (count > 0) {
    $page.variables.positive = (totalPositive / count).toFixed(2);
    $page.variables.negative = (totalNegative / count).toFixed(2);
    $page.variables.neutral = (totalNeutral / count).toFixed(2);
    $page.variables.mixed = (totalMixed / count).toFixed(2);

    $page.variables.chartDataArray[0].value = $page.variables.positive ;
    $page.variables.chartDataArray[1].value = $page.variables.negative ;
    $page.variables.chartDataArray[2].value = $page.variables.neutral ;
    $page.variables.chartDataArray[3].value = $page.variables.mixed ;
 
  }

  $page.variables.tableArray = allSentiments;
}




  }
  }
  return sentimentDetection;
});
