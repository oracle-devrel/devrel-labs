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

  class summarization extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      $page.variables.loading = true;

      const callRestAIIMeetingsPostV2Summarize2Result = await Actions.callRest(context, {
        endpoint: 'AIIMeetings/postV2Summarize2',
        body: {
      "documents": [$page.variables.transcriptionText]
      },
      });


      $page.variables.summaryText = callRestAIIMeetingsPostV2Summarize2Result.body;
      $page.variables.summaryStatus=true;
      $page.variables.loading = false;
    }
  }

  return summarization;
});
