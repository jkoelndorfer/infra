locals {
  environments = {
    dev = {
      zone   = "dev.johnk.io"
      domain = "dev.vaultwarden.johnk.io"
    }
    prod = {
      zone   = "johnk.io"
      domain = "vaultwarden.johnk.io"

      records = {
        mx = {
          name  = "em8945"
          value = "10 mx.sendgrid.net"
        }
        spf = {
          name  = "em8945"
          value = "v=spf1 include:sendgrid.net ~all"
        }
        dkim = {
          name  = "m1._domainkey"
          value = "k=rsa; t=s; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDODx75mrJ5cjG3jT1J5hd1mBE1VLRcEDMVocqvl2H/oUDiKzOLEmCO7Xh/FsFoYEqk8wMNPHbo04AKVtXbRSjFh2YMf90fVCs7krGSbunlcnUulK23gtUgSzRL413SgbUvp2tC9d1UA9vzVGpwZITR3wxzToFr2zMQEa45COJwdwIDAQAB"
        }
      }
    }
  }
}
