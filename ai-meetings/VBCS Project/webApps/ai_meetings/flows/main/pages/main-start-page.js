define([], () => {
  'use strict';


  class PageModule {




    
  
   receiveMessage(param,message) {
    const chatWindow = document.getElementById('chat-window');
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message');
    messageElement.classList.add(param === 'AI' ? 'AI' : 'You');
    messageElement.innerHTML = `<strong>${param}:</strong> ${message}`;
    chatWindow.appendChild(messageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return true;
    }    

  
   sendMessage(param,message) {
    const chatWindow = document.getElementById('chat-window');
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message');
    messageElement.classList.add(param === 'You' ? 'You' : 'AI');
    messageElement.innerHTML = `<strong>${param}:</strong> ${message}`;
    chatWindow.appendChild(messageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    }

  receiveTranscriptionMessage(param,message) {
    const chatWindow = document.getElementById('chat-t-window');
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-t-message');
    messageElement.classList.add(param);
    messageElement.innerHTML = `<strong>${param}:</strong> ${message}`;
    chatWindow.appendChild(messageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    }    

  
   sendTranscriptionMessage(param,message) {
    const chatWindow = document.getElementById('chat-t-window');
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-t-message');
     let title="Speaker "+param;
    if (param % 2 === 0)
    {
      messageElement.classList.add('Speaker2');
    }else{
      messageElement.classList.add('Speaker1');
    }

   
    
    messageElement.innerHTML = `<strong>${title}:</strong> ${message}`;
    chatWindow.appendChild(messageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    }


/*
processEntities(data,personEntities,orgEntities) {
   let personEntities2 =personEntities;
    let orgEntities2 = orgEntities;  
     
    data.documents[0].entities.forEach(entity => {
        if (entity.type === "PERSON") {
            personEntities2.push(entity.text);
        } else if (entity.type === "ORGANIZATION") {
            orgEntities2.push(entity.text);
        }
    });
// Elimina duplicados usando Set
    personEntities2 = [...new Set(personEntities2)];
    orgEntities2 = [...new Set(orgEntities2)];
    
    let json = {"personEntities": personEntities2, "orgEntities": orgEntities2};
//alert(JSON.stringify(json));
    return json; // Retorna el objeto JSON directamente
}
*/

     processText(text) {

      if (!text) {
        return '';
      }
     // Elimina las frases específicas
    const phrasesToRemove = [
        "Would you like help with anything else involving this text?",
        "Does this summary match what you were looking for?",
        "Is there anything else I can extract from the text?"
    ];

    phrasesToRemove.forEach(phrase => {
        text = text.replace(phrase, '');
    });
    // Reemplaza los guiones seguidos de un espacio con guiones y un salto de línea
    let processedText = text.replace(/- /g, ' <br> -');
    return processedText;
    }
  }
  
  return PageModule;
});
