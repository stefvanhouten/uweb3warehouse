
window.addEventListener('load', (event) => {
  attachpasswordreset();
});

var password;
var passwordconfirm;
function attachpasswordreset(){
  let forms = document.querySelectorAll('form[action="/setup"], form[action^="/resetpassword/"]');
  forms.forEach(form => {
    var hostname = form.querySelector('input[name="hostname"]');
    if(hostname){
      hostname.value = location.hostname;
    }

    password = form.querySelector('input[name="password"]');
    passwordconfirm = form.querySelector('input[name="password_confirm"]');
    password.addEventListener('change', handlepasswordchange);
    passwordconfirm.addEventListener('change', handlepasswordchange);
  });
}

function handlepasswordchange(event){
  if(password.value=='' || passwordconfirm.value==''){
      return false;
  }
  if(password.value != passwordconfirm.value){
    password.setCustomValidity('Passwords should be the same.');
    password.classList.add('error');
    password.classList.remove('succes');
    passwordconfirm.setCustomValidity('Passwords should be the same.');
    passwordconfirm.classList.add('error');
    passwordconfirm.classList.remove('succes');
  } else {
    password.setCustomValidity('');
    password.classList.remove('error');
    password.classList.add('succes');
    passwordconfirm.setCustomValidity('');
    passwordconfirm.classList.remove('error');
    passwordconfirm.classList.add('succes');
  }
}
