from warehouse.login import login

urls = [
    ("/login", (login.PageMaker, "HandleLogin"), "POST"),
    ("/logout", (login.PageMaker, "RequestLogout")),
    ("/usersettings", (login.PageMaker, "RequestUserSettings")),
    ("/resetpassword", (login.PageMaker, "RequestResetPassword")),
    ("/resetpassword/([^/]*)/(.*)", (login.PageMaker, "RequestResetPassword")),
]
