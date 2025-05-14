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

  class ButtonActionSendChat extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      await $page.functions.sendMessage('You', $page.variables.query);

      const callRestAIIMeetingsPostResult = await Actions.callRest(context, {
        endpoint: 'AIIMeetings/post',
        uriParams: {
          'conv_id': $page.variables.meetingID,
        },
        body: {
          query: $page.variables.query,
          documents: [
            $page.variables.transcriptionText,
          ],
        },
      });

      $page.variables.ragResponse = callRestAIIMeetingsPostResult.body;
       const result = await $page.functions.receiveMessage('AI', callRestAIIMeetingsPostResult.body);

      if ('result') {
       await Actions.resetVariables(context, {
         variables: [
           '$page.variables.query',
         ],
       });
     }

      return;
      


    }
  }

  return ButtonActionSendChat;
});
